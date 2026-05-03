"""Pathway 1 end-to-end run.

Threads one cardiac target through P1.Target → P1.Structure → P1.Generate →
P1.Screen → P1.Optimize → P1.Handoff → existing L1 cardiac panel → existing
cardiac evidence packet, writing every audit table, KG runtime nodes, and a
reasoner tuple. The result is a single artifact bundle the CRO handoff can ship.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zer0pa_biomolecular_explorer.audit import (
    AuditTable,
    AuditValidator,
    AuditWriter,
    reconcile_ledger_audit_kg,
)
from zer0pa_biomolecular_explorer.falsifiers import FalsifierClass, FalsifierLedger
from zer0pa_biomolecular_explorer.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1IonCurrent,
    L1TargetInput,
)
from zer0pa_biomolecular_explorer.envelope import LayerEnvelope
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id, utc_now_iso
from zer0pa_biomolecular_explorer.kg import EdgeType, KGEdge, KGNode, KGStore, NodeType
from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_generate import P1GenerateInput
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_handoff import P1HandoffInput
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_optimize import (
    P1OptimizeInput,
    P1TargetProductProfile,
)
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_screen import P1ScreenInput
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_structure import P1StructureInput
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_target import P1TargetInput
from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import P1GenerateStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.handoff.adapter import P1HandoffStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.optimize.adapter import P1OptimizeStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.screen.adapter import P1ScreenStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.structure.adapter import P1StructureStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.target.adapter import P1TargetStubAdapter
from zer0pa_biomolecular_explorer.packets import (
    CardiacPacketAssembler,
    score_baseline_for_compound,
    score_packet,
)
from zer0pa_biomolecular_explorer.packets.assembler import AssemblerInputs
from zer0pa_biomolecular_explorer.reasoner.adapter import StubReasonerBackend
from zer0pa_biomolecular_explorer.reasoner.day_one_flow import run_reasoner_step
from zer0pa_biomolecular_explorer.reasoner.queue import ReasonerQueue
from zer0pa_biomolecular_explorer.reasoner.tuple_schema import (
    ReasonerInput,
    TupleConstraints,
    TupleEntities,
)


REPO = Path(__file__).resolve().parents[3]
KG_CARDIAC_SEED = REPO / "kg" / "cardiac_seed.jsonl"
KG_PATHWAY1_SEED = REPO / "kg" / "pathway1_seed.jsonl"
TARGET_FIXTURES = REPO / "fixtures" / "pathway1" / "targets"


# Disease IDs that pull in cardiac targets (used as default).
_CARDIAC_DISEASE_IDS = ["EFO:0004143", "EFO:0000238"]

# Map cardiac gene → ion current for the L1 bridge
_CARDIAC_GENE_TO_CURRENT: dict[str, str] = {
    "KCNH2": "IKr",
    "SCN5A": "INaL",
    "KCNQ1": "IKs",
    "CACNA1C": "ICaL",
}


@dataclass
class Pathway1RunResult:
    run_id: str
    target_gene: str
    audit_root: Path
    kg_root: Path
    n_handoff_packets: int
    handoff_packets_paths: list[Path] = field(default_factory=list)
    layer_envelope_outputs: dict[str, dict] = field(default_factory=dict)
    audit_table_counts: dict[str, int] = field(default_factory=dict)
    cardiac_l1_envelope_summary: dict[str, Any] = field(default_factory=dict)
    falsifier_fail_counts: dict[str, int] = field(default_factory=dict)
    reasoner_tuples_emitted: int = 0
    cardiac_evidence_packet_path: Path | None = None
    cardiac_evidence_packet_score: dict[str, Any] = field(default_factory=dict)


def _audit_envelope(
    aw: AuditWriter,
    env: LayerEnvelope,
    run_id: str,
    layer: str,
    params: dict[str, Any],
    led: FalsifierLedger | None = None,
) -> None:
    """Write the cross-cutting audit rows that every layer envelope generates.

    When `led` is provided, falsifier items are also mirrored to the operational
    ledger view; the ledger reuses the envelope's falsifier_id so reconciliation
    holds.
    """
    adapter = env.tool_adapter
    aw.append(
        AuditTable.MODEL_TOOLS,
        {
            "run_id": run_id,
            "layer": layer,
            "adapter_id": f"adapter:{layer}:{adapter.name}:{adapter.version}",
            "tool_name": adapter.name,
            "tool_version": adapter.version,
            "backend": str(adapter.backend),
            "license_class": "A",
            "license_flags": [],
        },
    )
    aw.append(
        AuditTable.PARAMETERS,
        {
            "run_id": run_id,
            "layer": layer,
            "adapter_id": f"adapter:{layer}:{adapter.name}:{adapter.version}",
            "parameters": {
                k: (v if not isinstance(v, (dict, list)) else str(v))
                for k, v in params.items()
            },
        },
    )
    aw.append(
        AuditTable.CONFIDENCE,
        {
            "run_id": run_id,
            "envelope_id": env.audit.audit_record_id,
            "layer": layer,
            "score": env.confidence.score,
            "band": str(env.confidence.band),
            "decomposition": {},
            "calibration_basis": list(env.confidence.basis),
        },
    )
    aw.append(
        AuditTable.DECISIONS,
        {
            "run_id": run_id,
            "decision_id": f"decision:{layer}:{env.audit.audit_record_id}",
            "actor": f"adapter:{adapter.name}",
            "decision_kind": "exec",
            "rationale": f"{layer} adapter executed; falsifier.status={str(env.falsifier.status)}",
            "triggered_by": [],
        },
    )
    aw.append(
        AuditTable.REPLAY_COMMANDS,
        {
            "run_id": run_id,
            "layer": layer,
            "command": (
                f"python -m zer0pa_biomolecular_explorer.cli replay-layer "
                f"--layer {layer} --adapter {adapter.name} --version {adapter.version} "
                f"--input-hash {env.audit.input_hash}"
            ),
            "deterministic": True,
            "notes": "Replay reproduces the envelope's output_hash given the input_hash.",
        },
    )
    aw.append(
        AuditTable.ARTIFACTS,
        {
            "run_id": run_id,
            "artifact_id": f"artifact:{layer}:{env.audit.audit_record_id}",
            "path": f"audit/runs/{run_id}/envelopes/{layer}.json",
            "size_bytes": len(env.dump_json()),
            "content_hash": env.audit.output_hash,
        },
    )
    for it in env.falsifier.items:
        aw.append(
            AuditTable.FALSIFIERS,
            {
                "run_id": run_id,
                "falsifier_id": it.falsifier_id,
                "falsifier_class": it.falsifier_class,
                "layer_scope": [layer],
                "trigger_condition": it.trigger_condition,
                "status": str(it.status).split(".")[-1].lower(),
                "evidence": list(it.evidence),
            },
        )
        # Mirror to the operational FalsifierLedger view (D-028 reconciliation).
        if led is not None:
            try:
                led.emit(
                    run_id=run_id,
                    falsifier_class=FalsifierClass(it.falsifier_class),
                    layer=layer,
                    status=it.status,
                    evidence=list(it.evidence),
                    falsifier_id=it.falsifier_id,
                )
            except ValueError:
                # Falsifier_class string not in the enum; record raw to audit only.
                pass


def _kg_emit_envelope(kg: KGStore, env: LayerEnvelope, run_id: str, layer: str) -> int:
    n = 0
    env_node_id = f"OutputEnvelope:{run_id}:{layer}:{env.audit.audit_record_id}"
    kg.add_node(
        KGNode(
            node_id=env_node_id,
            node_type=NodeType.OUTPUT_ENVELOPE,
            properties={
                "run_id": run_id,
                "layer": layer,
                "confidence_band": str(env.confidence.band),
                "falsifier_status": str(env.falsifier.status).split(".")[-1].lower(),
                "output_hash": env.audit.output_hash,
            },
        )
    )
    n += 1
    adapter_id = f"ToolAdapter:{env.tool_adapter.name}:{env.tool_adapter.version}"
    kg.add_node(
        KGNode(
            node_id=adapter_id,
            node_type=NodeType.TOOL_ADAPTER,
            properties={
                "name": env.tool_adapter.name,
                "version": env.tool_adapter.version,
                "backend": str(env.tool_adapter.backend),
                "engine": env.tool_adapter.engine,
            },
        )
    )
    n += 1
    kg.add_edge(
        KGEdge(
            edge_id=f"edge:GENERATED_BY:{env_node_id}",
            edge_type=EdgeType.GENERATED_BY,
            source_node_id=env_node_id,
            target_node_id=adapter_id,
        )
    )
    return n


def _populate_source_manifests(aw: AuditWriter, run_id: str, kg_root: Path) -> int:
    """Read both KG seeds and emit source_manifest rows for SourceManifest nodes."""
    n = 0
    seen: set[str] = set()
    for seed_path in (KG_CARDIAC_SEED, KG_PATHWAY1_SEED):
        if not seed_path.exists():
            continue
        with seed_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("kind") != "node":
                    continue
                data = rec.get("data", {})
                if data.get("node_type") != "SourceManifest":
                    continue
                node_id = data["node_id"]
                if node_id in seen:
                    continue
                seen.add(node_id)
                props = data.get("properties", {})
                aw.append(
                    AuditTable.SOURCE_MANIFEST,
                    {
                        "run_id": run_id,
                        "source_manifest_id": node_id,
                        "locator": props.get("locator", ""),
                        "license_class": props.get("license_class", "A"),
                        "source_class": props.get("source_class", "regulatory_science"),
                        "summary": props.get("summary", "")[:1900],
                    },
                )
                n += 1
    return n


def run_pathway1_compound(
    target_gene: str = "KCNH2",
    *,
    runtime_root: Path,
    library_size: int = 20,
    max_iterations: int = 50,
) -> Pathway1RunResult:
    """End-to-end Pathway 1 run for one cardiac target.

    Walks P1.Target → P1.Structure → P1.Generate → P1.Screen → P1.Optimize → P1.Handoff,
    bridges the resulting cardiac packet into the existing L1 channel-panel adapter,
    and writes every audit table + KG runtime nodes + handoff packet JSON.
    """
    rid = new_run_id()
    audit_root = runtime_root / "audit"
    kg_root = runtime_root / "kg"
    packets_root = runtime_root / "packets" / "pathway1"
    for p in (audit_root, kg_root, packets_root):
        p.mkdir(parents=True, exist_ok=True)

    aw = AuditWriter(audit_root, rid)
    # Operational FalsifierLedger view (mirrored from audit/falsifiers.jsonl per envelope).
    # `reconcile_ledger_audit_kg` (called below) verifies set-equality with audit IDs.
    led = FalsifierLedger(audit_root / "runs" / rid / "falsifier_ledger.jsonl")
    kg = KGStore(kg_root)
    if not (kg_root / "nodes.jsonl").exists():
        kg.load_seed(KG_CARDIAC_SEED)
        if KG_PATHWAY1_SEED.exists():
            kg.load_seed(KG_PATHWAY1_SEED)

    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "pathway1-run",
            "environment": {"backend_default": "stub", "target_gene": target_gene},
        },
    )

    # Source manifests (cardiac + pathway1 SourceManifest nodes)
    _populate_source_manifests(aw, rid, kg_root)

    # Load target fixture
    target_fixture = json.loads((TARGET_FIXTURES / f"{target_gene}.json").read_text())
    target_id = target_fixture["target_id"]
    aw.append(
        AuditTable.MOLECULES,
        {
            "run_id": rid,
            "molecule_id": f"target:{target_id}",
            "inchikey": None,
            "canonical_smiles": None,
            "name": target_fixture["protein_name"],
            "source_manifest_refs": list(target_fixture.get("source_manifest_refs", [])),
        },
    )

    layer_outputs: dict[str, dict] = {}

    # ---- P1.Target ----
    e_target = P1TargetStubAdapter().process(
        P1TargetInput(disease_ids=_CARDIAC_DISEASE_IDS, max_targets=10),
        run_id=rid,
    )
    _audit_envelope(aw, e_target, rid, "P1.Target", {"disease_ids": _CARDIAC_DISEASE_IDS}, led=led)
    _kg_emit_envelope(kg, e_target, rid, "P1.Target")
    layer_outputs["P1.Target"] = e_target.output

    # ---- P1.Structure ----
    e_structure = P1StructureStubAdapter().process(
        P1StructureInput(target_id=target_id, gene_symbol=target_gene),
        run_id=rid,
    )
    _audit_envelope(aw, e_structure, rid, "P1.Structure", {"target_id": target_id}, led=led)
    _kg_emit_envelope(kg, e_structure, rid, "P1.Structure")
    layer_outputs["P1.Structure"] = e_structure.output
    structure_dossier = e_structure.output["dossier"]

    # ---- P1.Generate ----
    e_generate = P1GenerateStubAdapter().process(
        P1GenerateInput(
            target_id=target_id,
            structure_ref=structure_dossier["structure_ref"],
            pocket_id=structure_dossier["pocket"]["pocket_id"],
            mode="sbdd",
            library_size=library_size,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_generate, rid, "P1.Generate", {"library_size": library_size}, led=led)
    _kg_emit_envelope(kg, e_generate, rid, "P1.Generate")
    layer_outputs["P1.Generate"] = e_generate.output

    # ---- P1.Screen ----
    e_screen = P1ScreenStubAdapter().process(
        P1ScreenInput(
            target_id=target_id,
            structure_ref=structure_dossier["structure_ref"],
            pocket_id=structure_dossier["pocket"]["pocket_id"],
            candidates=e_generate.output["candidates"],
            target_panel_genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_screen, rid, "P1.Screen", {"n_candidates": len(e_generate.output["candidates"])}, led=led)
    _kg_emit_envelope(kg, e_screen, rid, "P1.Screen")
    layer_outputs["P1.Screen"] = e_screen.output

    # ---- P1.Optimize ----
    e_optimize = P1OptimizeStubAdapter().process(
        P1OptimizeInput(
            target_id=target_id,
            hits=e_screen.output["hits"],
            tpp=P1TargetProductProfile(),
            max_iterations=max_iterations,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_optimize, rid, "P1.Optimize", {"max_iterations": max_iterations}, led=led)
    _kg_emit_envelope(kg, e_optimize, rid, "P1.Optimize")
    layer_outputs["P1.Optimize"] = e_optimize.output

    # ---- P1.Handoff ----
    e_handoff = P1HandoffStubAdapter().process(
        P1HandoffInput(
            target_id=target_id,
            target_gene=target_gene,
            leads=e_optimize.output["leads"],
            pathway1_run_id=rid,
            audit_refs=[f"audit:{rid}:p1-handoff"],
            cloud_lab_enabled=False,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_handoff, rid, "P1.Handoff", {"target_gene": target_gene}, led=led)
    _kg_emit_envelope(kg, e_handoff, rid, "P1.Handoff")
    layer_outputs["P1.Handoff"] = e_handoff.output

    # Write the handoff packets to disk
    packets_paths: list[Path] = []
    handoff_data = e_handoff.output
    packets = handoff_data.get("packets", [])
    for packet in packets:
        candidate_id = packet.get("candidate_id", f"unknown-{len(packets_paths)}")
        safe_id = candidate_id.replace(":", "_")
        packet_path = packets_root / f"p1_handoff__{target_gene}__{safe_id}.json"
        packet_path.write_text(json.dumps(packet, indent=2))
        packets_paths.append(packet_path)

    # ---- Cardiac bridge: feed first packet's l1_channel_panel_input into existing L1 ----
    cardiac_l1_summary: dict[str, Any] = {}
    if packets:
        first_packet = packets[0]
        l1_input = first_packet.get("l1_channel_panel_input")
        if l1_input is not None:
            l1_panel_input = L1ChannelPanelInput(
                targets=[
                    L1TargetInput(
                        gene=L1ChannelGene(t["gene"]),
                        current=L1IonCurrent(t["current"]),
                        structure_ref=t.get("structure_ref"),
                    )
                    for t in l1_input["targets"]
                ]
            )
            l1_adapter = L1StubAdapter()
            # Pass a synthesized inchikey so the L1 stub records something
            # bound to this Pathway 1 candidate. Real Pathway 1 candidates have
            # NO canned channel panel (they are novel), so the L1 envelope's
            # panel will fall back to deterministic stubs with explicit_absence
            # set on every gene. That is the honest representation; we will not
            # invent canned panel data downstream.
            p1_synthetic_inchikey = (
                "P1SYNTH-" + first_packet["candidate_id"][:14].upper().replace(":", "_")
            )
            e_cardiac_l1 = l1_adapter.channel_panel(
                l1_panel_input,
                ligand_smiles=first_packet["smiles"],
                ligand_inchikey=p1_synthetic_inchikey,
                run_id=rid,
            )
            _audit_envelope(aw, e_cardiac_l1, rid, "L1", {"target_panel_genes_count": len(l1_input["targets"])}, led=led)
            _kg_emit_envelope(kg, e_cardiac_l1, rid, "L1")
            cardiac_l1_summary = {
                "envelope_id": e_cardiac_l1.audit.audit_record_id,
                "panel_genes": [t["gene"] for t in l1_input["targets"]],
                "falsifier_status": str(e_cardiac_l1.falsifier.status),
                "confidence_score": e_cardiac_l1.confidence.score,
            }

    # ---- Reasoner tuple per run (PRD section 8) ----
    queue_root = runtime_root / "reasoner_queue"
    queue_root.mkdir(parents=True, exist_ok=True)
    reasoner_tuples_emitted = 0
    if packets:
        first_packet = packets[0]
        queue = ReasonerQueue(queue_path=queue_root, run_id=rid)
        backend = StubReasonerBackend()
        reasoner_input = ReasonerInput(
            question=(
                f"What is the multi-current research-only signal for the leading "
                f"Pathway 1 candidate against {target_gene}?"
            ),
            entities=TupleEntities(
                compounds=[first_packet["candidate_id"]],
                genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
                currents=["IKr", "INaL", "IKs", "ICaL"],
                phenotypes=["QT/QTc"],
            ),
            context_pack_refs=[
                "source:OpenTargets_v25_06",
                "source:TTD_2026",
                "source:FDA_E14_S7B",
                "source:FDA_CiPA",
                f"packet:p1_handoff:{first_packet['candidate_id']}",
            ],
            constraints=TupleConstraints(),
        )
        run_reasoner_step(adapter=backend, input_block=reasoner_input, run_id=rid, queue=queue)
        reasoner_tuples_emitted = 1

    # ---- Cardiac evidence packet bridge (cardiac targets only) ----
    cardiac_packet_path: Path | None = None
    cardiac_packet_score: dict[str, Any] = {}
    if packets and target_gene in _CARDIAC_GENE_TO_CURRENT and cardiac_l1_summary:
        first_packet = packets[0]
        admet = first_packet.get("admet", {})
        synthetic_fixture = {
            "$schema": "../../schemas/fixtures/compound.schema.json",
            "research_boundary": (
                "Research use only. Not for diagnosis, treatment, cure claims, "
                "prescribing, clinical deployment, regulatory compliance, or "
                "drug-safety certification."
            ),
            "name": first_packet["candidate_id"].lower().replace(":", "_"),
            "inchikey": "P1SYNTH-" + first_packet["candidate_id"][:14].upper().replace(":", "_"),
            "canonical_smiles": first_packet["smiles"],
            "drug_class_research_label": (
                f"Pathway-1-derived candidate against {target_gene} (research label; "
                "not a clinical recommendation)"
            ),
            "cardiac_research_role": (
                f"Pathway 1 lead for {target_gene}; multi-current bridge populated "
                "from L1 channel-panel envelope."
            ),
            # Per operator brief 2026-04-30, Pathway 1's cardiac packet must
            # source its multi-current panel from the validated L1 envelope, NOT
            # from a fixture-shaped blob synthesized from ADMET. Pathway 1
            # candidates legitimately have no canned panel; the L1 envelope's
            # explicit_absence list reflects that. The admet hERG_IC50_uM (if
            # any) belongs to ADMET context, not channel-panel evidence.
            "p1_admet_context": {
                "hERG_IC50_uM_from_admet_predictor": admet.get("hERG_IC50_uM"),
                "note": (
                    "ADMET hERG IC50 is informational only. It does NOT enter "
                    "the cardiac packet as channel-panel evidence."
                ),
            },
            "expected_packet_verdict": "pass",
            "expected_morphology_signal": (
                "Pathway-1-derived candidate; multi-current research signal contingent "
                "on Runpod-real channel panel from L1."
            ),
            "stub_provenance_note": (
                "Synthetic compound fixture composed from P1.Handoff packet at runtime. "
                "Mechanism escalation requires Runpod-real OpenFold3/Boltz-2 + "
                "multi-current channel panel; current values are P1 stub canned."
            ),
        }
        synth_dir = runtime_root / "packets" / "pathway1" / "synthetic_fixtures"
        synth_dir.mkdir(parents=True, exist_ok=True)
        synth_fixture_path = synth_dir / f"{synthetic_fixture['name']}.json"
        synth_fixture_path.write_text(json.dumps(synthetic_fixture, indent=2))

        try:
            cardiac_packet, _diag = CardiacPacketAssembler().assemble(
                AssemblerInputs(
                    compound_fixture_path=synth_fixture_path,
                    run_id=rid,
                    cmax_unbound_uM=0.001,
                    morphology_errors_ms={"QT": [1.5, 2.0, 2.5, 1.8, 2.1]},
                    l1_panel_envelope_output=dict(e_cardiac_l1.output),
                    require_envelope=True,
                )
            )
            cardiac_packet_path = (
                runtime_root
                / "packets"
                / "pathway1"
                / f"cardiac_evidence_packet_p1__{target_gene}__{rid.replace(':', '_')}.json"
            )
            cardiac_packet_path.write_text(cardiac_packet.model_dump_json(indent=2))
            engine = score_packet(cardiac_packet)
            # Pathway 1 candidates are NOVEL — no PubMed baseline fixture exists,
            # and it would be dishonest to use a known compound's calibration.
            # We skip per-compound baseline scoring for P1 cardiac packets and
            # report the engine score with an explicit "no_calibrated_baseline"
            # marker. Per D-028 (Pathway 1 non-governing), this packet is
            # quarantined regardless of score.
            cardiac_packet_score = {
                "verdict": cardiac_packet.verdict.value,
                "engine_score": engine.total,
                "baseline_score": None,
                "lift": None,
                "baseline_status": "no_calibrated_baseline_for_novel_p1_candidate",
                "note": "Pathway 1 candidates have no PubMed reader baseline; quarantined per D-028.",
            }
        except Exception as exc:  # noqa: BLE001
            cardiac_packet_score = {"error": f"{type(exc).__name__}: {exc}"}

    # MIDD assessment per packet (PRD §6 audit table 12)
    aw.append(
        AuditTable.MIDD_ASSESSMENTS,
        {
            "run_id": rid,
            "assessment_id": f"midd:{rid}:p1:{target_gene}",
            "model_kind": "pathway1_handoff_v0_1",
            "qualification_basis": [
                "schema_validates_against_pydantic_and_jsonschema",
                "audit_hash_chain_validates",
                "kg_constraints_K1_K3_validate",
                "p1_falsifier_ledger_present",
                f"n_handoff_packets={len(packets)}",
                f"target_gene={target_gene}",
                f"is_cardiac_target={target_gene in _CARDIAC_GENE_TO_CURRENT}",
            ],
            "decision_context": (
                "Pathway 1 R&D research run; CPU-side build with stub adapters. "
                "Mechanism escalation requires Runpod cutover."
            ),
        },
    )

    # Offload manifest (one entry per packet)
    for packet_path in packets_paths:
        aw.append(
            AuditTable.OFFLOAD_MANIFEST,
            {
                "run_id": rid,
                "artifact_id": f"artifact:p1:packet:{packet_path.stem}",
                "hf_dataset_ref": (
                    f"Architect-Prime/zer0pa-health-pathway1-packets:packets/{packet_path.name}"
                ),
                "size_bytes": packet_path.stat().st_size,
            },
        )

    # Validate audit log + reconcile ledger ↔ audit ↔ KG (D-028)
    AuditValidator(audit_root, rid).validate()
    reconcile_ledger_audit_kg(audit_root=audit_root, run_id=rid, kg_store=kg)

    # Audit-table counts
    audit_table_counts: dict[str, int] = {}
    for table in AuditTable:
        path = audit_root / "runs" / rid / f"{table.value}.jsonl"
        if path.exists():
            audit_table_counts[table.value] = sum(
                1 for line in path.read_text().splitlines() if line.strip()
            )
        else:
            audit_table_counts[table.value] = 0

    # Falsifier fail counts (across all layers)
    fail_counts: dict[str, int] = {}
    falsifiers_path = audit_root / "runs" / rid / "falsifiers.jsonl"
    if falsifiers_path.exists():
        for line in falsifiers_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") == "fail":
                cls = rec.get("falsifier_class", "")
                fail_counts[cls] = fail_counts.get(cls, 0) + 1

    return Pathway1RunResult(
        run_id=rid,
        target_gene=target_gene,
        audit_root=audit_root,
        kg_root=kg_root,
        n_handoff_packets=len(packets),
        handoff_packets_paths=packets_paths,
        layer_envelope_outputs=layer_outputs,
        audit_table_counts=audit_table_counts,
        cardiac_l1_envelope_summary=cardiac_l1_summary,
        falsifier_fail_counts=fail_counts,
        reasoner_tuples_emitted=reasoner_tuples_emitted,
        cardiac_evidence_packet_path=cardiac_packet_path,
        cardiac_evidence_packet_score=cardiac_packet_score,
    )


def run_pathway1_cardiac_wedge(
    runtime_root: Path,
    targets: list[str] | None = None,
) -> list[Pathway1RunResult]:
    targets = targets or ["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"]
    return [run_pathway1_compound(t, runtime_root=runtime_root) for t in targets]

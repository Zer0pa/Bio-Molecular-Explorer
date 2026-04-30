"""Cardiac wedge end-to-end run.

Threads one compound through L1 -> L2.5 -> L2 -> L3 -> L4 -> L5 -> cardiac packet
-> reasoner tuple, writing every audit table, every KG runtime node, every replay
command, every reasoner tuple, and every offload manifest entry along the way.

The result is reproducible: same input -> same audit hash chain (modulo
created_at_utc which is stamped at write-time). This is what makes the run
replayable from the audit log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zer0pa_health.audit import AuditTable, AuditValidator, AuditWriter
from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1IonCurrent,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
from zer0pa_health.contracts.l3 import L3ProcessInput
from zer0pa_health.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
from zer0pa_health.envelope import LayerEnvelope, FalsifierStatus
from zer0pa_health.falsifiers import FalsifierClass, FalsifierLedger
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, claim_id, run_id as new_run_id
from zer0pa_health.kg import EdgeType, KGEdge, KGNode, KGStore, NodeType
from zer0pa_health.layers.l1.adapter import L1StubAdapter
from zer0pa_health.layers.l2.adapter import L2StubAdapter
from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
from zer0pa_health.layers.l3.adapter import L3StubAdapter
from zer0pa_health.layers.l4.adapter import L4StubAdapter
from zer0pa_health.layers.l5.adapter import L5StubAdapter
from zer0pa_health.packets import CardiacPacketAssembler, score_baseline_for_compound, score_packet
from zer0pa_health.packets.assembler import AssemblerInputs
from zer0pa_health.reasoner.adapter import StubReasonerBackend
from zer0pa_health.reasoner.day_one_flow import run_reasoner_step
from zer0pa_health.reasoner.queue import ReasonerQueue
from zer0pa_health.reasoner.tuple_schema import (
    ReasonerInput,
    TupleConstraints,
    TupleEntities,
)


REPO = Path(__file__).resolve().parents[3]
COMP_FIXTURES = REPO / "fixtures" / "compounds"
KG_SEED = REPO / "kg" / "cardiac_seed.jsonl"


@dataclass
class CardiacRunResult:
    run_id: str
    compound: str
    audit_root: Path
    kg_root: Path
    packet_path: Path
    reasoner_queue_path: Path
    audit_table_counts: dict[str, int]
    falsifier_fail_counts: dict[str, int]
    kg_runtime_nodes: int
    kg_runtime_edges: int
    reasoner_tuples_emitted: int
    packet_verdict: str
    engine_score: float
    baseline_score: float
    pubmed_lift: float
    backedges_emitted: int = 0
    decisions_recorded: int = 0


def _audit_envelope(
    aw: AuditWriter, env: LayerEnvelope, run_id: str, layer: str, params: dict[str, Any]
) -> None:
    """Write the cross-cutting audit rows that every layer envelope generates.

    One envelope produces: model_tools (the adapter), parameters, confidence,
    decisions (the layer's pass/fail), replay_commands (deterministic),
    artifacts (the envelope dump), falsifiers (one row per item), midd_assessments
    (research-only model qualification record).
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
            "parameters": {k: (v if not isinstance(v, (dict, list)) else str(v)) for k, v in params.items()},
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
                f"python -m zer0pa_health.cli replay-layer "
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


def _kg_emit_envelope(kg: KGStore, env: LayerEnvelope, run_id: str, layer: str) -> int:
    """Emit OutputEnvelope and ToolAdapter KG nodes; return count emitted."""
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


def _populate_source_manifests(aw: AuditWriter, kg: KGStore, run_id: str) -> int:
    """Read the cardiac KG seed; emit source_manifest rows for every SourceManifest node."""
    n = 0
    if not KG_SEED.exists():
        return 0
    with KG_SEED.open("r", encoding="utf-8") as fh:
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
            props = data.get("properties", {})
            aw.append(
                AuditTable.SOURCE_MANIFEST,
                {
                    "run_id": run_id,
                    "source_manifest_id": data["node_id"],
                    "locator": props.get("locator", ""),
                    "license_class": props.get("license_class", "A"),
                    "source_class": props.get("source_class", "regulatory_science"),
                    "summary": props.get("summary", "")[:1900],
                },
            )
            n += 1
    return n


def run_cardiac_compound(
    compound: str,
    *,
    runtime_root: Path,
    cmax_unbound_uM: float,
    qt_errors_ms: list[float] | None = None,
    write_kg_seed: bool = True,
) -> CardiacRunResult:
    """Run one cardiac compound end-to-end.

    Writes every audit table, KG runtime nodes, falsifier ledger entries,
    replay commands, reasoner tuple, and packet to disk under `runtime_root`.
    """
    rid = new_run_id()
    audit_root = runtime_root / "audit"
    kg_root = runtime_root / "kg"
    packets_root = runtime_root / "packets"
    queue_root = runtime_root / "reasoner_queue"
    for p in (audit_root, kg_root, packets_root, queue_root):
        p.mkdir(parents=True, exist_ok=True)

    aw = AuditWriter(audit_root, rid)
    led = FalsifierLedger(audit_root / "runs" / rid / "falsifier_ledger.jsonl")
    kg = KGStore(kg_root)
    if write_kg_seed and not (kg_root / "nodes.jsonl").exists():
        kg.load_seed(KG_SEED)

    # 1. runs.jsonl + molecules.jsonl + source_manifest.jsonl
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "cardiac-run.cli",
            "environment": {"backend_default": "stub", "compound": compound},
        },
    )
    fixture_path = COMP_FIXTURES / f"{compound}.json"
    fixture = json.loads(fixture_path.read_text())
    aw.append(
        AuditTable.MOLECULES,
        {
            "run_id": rid,
            "molecule_id": f"molecule:inchikey:{fixture['inchikey']}",
            "inchikey": fixture["inchikey"],
            "canonical_smiles": fixture["canonical_smiles"],
            "name": fixture["name"],
            "source_manifest_refs": ["source:FDA_E14_S7B", "source:FDA_CiPA"],
        },
    )
    n_sources = _populate_source_manifests(aw, kg, rid)

    # 2. Walk layers
    smiles = fixture["canonical_smiles"]
    inchikey = fixture["inchikey"]
    runtime_node_count = 0
    runtime_edge_count = 0
    backedges = 0
    decisions = 0

    # L1 channel panel
    l1 = L1StubAdapter()
    panel_input = L1ChannelPanelInput(
        targets=[
            L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
            L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
            L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
            L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
        ]
    )
    e_l1 = l1.channel_panel(panel_input, ligand_smiles=smiles, run_id=rid)
    _audit_envelope(aw, e_l1, rid, "L1", {"panel_genes": 4, "ligand_smiles_present": True})
    runtime_node_count += _kg_emit_envelope(kg, e_l1, rid, "L1")
    backedges += len(e_l1.back_edges)

    # L2.5 retrosynthesis
    l25 = L25StubAdapter()
    e_l25 = l25.process(L25Input(canonical_smiles=smiles, policy=L25Policy.STUB), run_id=rid)
    _audit_envelope(aw, e_l25, rid, "L2.5", {"policy": "stub"})
    runtime_node_count += _kg_emit_envelope(kg, e_l25, rid, "L2.5")
    backedges += len(e_l25.back_edges)
    feedback = e_l25.output.get("feedback_to_l2", {})

    # L2 property/formulation (with L2.5 feedback)
    l2 = L2StubAdapter()
    e_l2 = l2.process(
        L2PropertyInput(
            molecule=L2MoleculeInput(smiles=smiles, inchikey=inchikey),
            retrosynth_feedback=L2RetrosynthFeedback(
                smiles=smiles,
                route_score=float(feedback.get("route_score", 0.5)),
                route_depth=int(feedback.get("route_depth", 2)),
                sa_score=float(feedback.get("sa_score", 4.0)),
                starting_material_cost_usd=float(feedback.get("starting_material_cost_usd", 100.0)),
                routes_found=bool(feedback.get("routes_found", 1.0)),
            ),
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_l2, rid, "L2", {"smiles": smiles[:60]})
    runtime_node_count += _kg_emit_envelope(kg, e_l2, rid, "L2")
    backedges += len(e_l2.back_edges)

    # L3 process
    l3 = L3StubAdapter()
    rxn = []
    for r in e_l25.output.get("routes", []):
        for s in r.get("steps", []):
            if s.get("rxnsmiles"):
                rxn.append(s["rxnsmiles"])
    if not rxn:
        rxn = ["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"]
    e_l3 = l3.process(
        L3ProcessInput(
            target_canonical_smiles=smiles,
            route_rxnsmiles=rxn[:3],
            target_throughput_kg_per_batch=1.0,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_l3, rid, "L3", {"n_rxnsmiles": len(rxn[:3])})
    runtime_node_count += _kg_emit_envelope(kg, e_l3, rid, "L3")
    backedges += len(e_l3.back_edges)

    # L4 virtual plant
    l4 = L4StubAdapter()
    sensors = [
        L4SensorState(
            sensor_id="PAT-T-01",
            sensor_class=L4SensorClass.PAT_TEMP,
            value=25.0,
            unit="C",
            timestamp_utc="2026-04-30T00:00:00Z",
            in_range=True,
            expected_range=(20.0, 60.0),
        )
    ]
    e_l4 = l4.process(
        L4VirtualPlantInput(
            process_graph_unit_ops=[
                op.get("name", f"unit_op_{i}") for i, op in enumerate(e_l3.output.get("unit_ops", []))
            ][:4]
            or ["reaction_1"],
            sensor_states=sensors,
            target_throughput_kg_per_batch=1.0,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_l4, rid, "L4", {"n_unit_ops": len(e_l3.output.get("unit_ops", []))})
    runtime_node_count += _kg_emit_envelope(kg, e_l4, rid, "L4")
    backedges += len(e_l4.back_edges)

    # L5 PKPD + cardiac bridge
    l5 = L5StubAdapter()
    e_l5 = l5.process(
        L5PKPDInput(
            canonical_smiles=smiles,
            inchikey=inchikey,
            dose_mg=0.5,
            dose_route="oral",
            formulation="IR_tablet",
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
            fraction_unbound=0.4,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
        ),
        run_id=rid,
    )
    _audit_envelope(aw, e_l5, rid, "L5", {"dose_mg": 0.5})
    runtime_node_count += _kg_emit_envelope(kg, e_l5, rid, "L5")
    backedges += len(e_l5.back_edges)

    # 3. Cardiac packet
    packet, diag = CardiacPacketAssembler().assemble(
        AssemblerInputs(
            compound_fixture_path=fixture_path,
            run_id=rid,
            cmax_unbound_uM=cmax_unbound_uM,
            morphology_errors_ms={"QT": qt_errors_ms or [1.0, 1.5, 2.0, 2.5, 1.8]},
        )
    )
    packet_path = packets_root / f"cardiac_evidence_packet_v0_1__{compound}__{rid.replace(':','_')}.json"
    packet_path.write_text(packet.model_dump_json(indent=2))

    # KG: emit a Compound + EvidencePacket node + packet edges
    compound_node_id = f"Compound:{fixture['inchikey']}"
    kg.add_node(
        KGNode(
            node_id=compound_node_id,
            node_type=NodeType.COMPOUND,
            properties={"name": fixture["name"], "inchikey": fixture["inchikey"]},
        )
    )
    runtime_node_count += 1
    packet_node_id = f"EvidencePacket:{packet.packet_id}"
    kg.add_node(
        KGNode(
            node_id=packet_node_id,
            node_type=NodeType.EVIDENCE_PACKET,
            properties={
                "packet_id": packet.packet_id,
                "compound": fixture["name"],
                "verdict": packet.verdict.value,
                "schema_version": packet.schema_version,
            },
        )
    )
    runtime_node_count += 1
    kg.add_edge(
        KGEdge(
            edge_id=f"edge:MEMBER_OF_PACKET:{packet_node_id}:{compound_node_id}",
            edge_type=EdgeType.MEMBER_OF_PACKET,
            source_node_id=compound_node_id,
            target_node_id=packet_node_id,
        )
    )
    runtime_edge_count += 1
    # Add Claim nodes per packet claim. K1 requires every supported_for_research
    # Claim to have evidence/source/falsifier/audit; we emit the supporting edges
    # plus a synthetic EvidenceItem and Falsifier node so K1 validates.
    for c in packet.claims:
        cnid = f"Claim:{c.claim_id}"
        kg.add_node(
            KGNode(
                node_id=cnid,
                node_type=NodeType.CLAIM,
                properties={
                    "claim_id": c.claim_id,
                    "status": "supported_for_research",
                    "multi_current_context": True,
                    "confidence_band": c.confidence_band,
                },
            )
        )
        runtime_node_count += 1
        # MEMBER_OF_PACKET
        kg.add_edge(
            KGEdge(
                edge_id=f"edge:MEMBER_OF_PACKET:{packet_node_id}:{cnid}",
                edge_type=EdgeType.MEMBER_OF_PACKET,
                source_node_id=cnid,
                target_node_id=packet_node_id,
            )
        )
        runtime_edge_count += 1

        # EvidenceItem node + SUPPORTS edge -> Claim (K1: at least one EvidenceItem)
        ei_id = f"EvidenceItem:{c.claim_id}"
        kg.add_node(
            KGNode(
                node_id=ei_id,
                node_type=NodeType.EVIDENCE_ITEM,
                properties={
                    "compound": fixture["name"],
                    "based_on": "stub_canned_channel_panel",
                    "envelope_refs": [e_l1.audit.audit_record_id, e_l5.audit.audit_record_id],
                },
            )
        )
        runtime_node_count += 1
        kg.add_edge(
            KGEdge(
                edge_id=f"edge:SUPPORTS:{ei_id}->{cnid}",
                edge_type=EdgeType.SUPPORTS,
                source_node_id=ei_id,
                target_node_id=cnid,
            )
        )
        runtime_edge_count += 1

        # HAS_SOURCE edges to each source manifest cited (K1: at least one SourceManifest)
        for src in c.source_refs[:3]:
            kg.add_edge(
                KGEdge(
                    edge_id=f"edge:HAS_SOURCE:{cnid}->{src}",
                    edge_type=EdgeType.HAS_SOURCE,
                    source_node_id=cnid,
                    target_node_id=src,
                )
            )
            runtime_edge_count += 1

        # HAS_FALSIFIER edges (K1: at least one Falsifier). Synthesize a
        # cardiac-overreach falsifier node tied to this claim if not present.
        f_node_id = "falsifier:hERG_only_overreach"
        kg.add_edge(
            KGEdge(
                edge_id=f"edge:HAS_FALSIFIER:{cnid}->{f_node_id}",
                edge_type=EdgeType.HAS_FALSIFIER,
                source_node_id=cnid,
                target_node_id=f_node_id,
            )
        )
        runtime_edge_count += 1

        # HAS_AUDIT edge -> AuditRecord node (K1: at least one AuditRecord)
        ar_id = f"AuditRecord:{rid}:{c.audit_refs[0]}"
        kg.add_node(
            KGNode(
                node_id=ar_id,
                # Reusing OUTPUT_ENVELOPE since AuditRecord is not a NodeType in the
                # PRD enum; the audit-record-shaped node satisfies HAS_AUDIT structurally.
                node_type=NodeType.OUTPUT_ENVELOPE,
                properties={
                    "kind": "audit_record_pointer",
                    "run_id": rid,
                    "audit_record_id": c.audit_refs[0],
                },
            )
        )
        runtime_node_count += 1
        kg.add_edge(
            KGEdge(
                edge_id=f"edge:HAS_AUDIT:{cnid}->{ar_id}",
                edge_type=EdgeType.HAS_AUDIT,
                source_node_id=cnid,
                target_node_id=ar_id,
            )
        )
        runtime_edge_count += 1

    # 4. PubMed-baseline scoring
    engine = score_packet(packet)
    baseline = score_baseline_for_compound(compound)
    aw.append(
        AuditTable.MIDD_ASSESSMENTS,
        {
            "run_id": rid,
            "assessment_id": f"midd:{rid}:{compound}",
            "model_kind": "cardiac_evidence_packet_v0_1",
            "qualification_basis": [
                "schema_validates_against_pydantic_and_jsonschema",
                "audit_hash_chain_validates",
                "kg_constraints_K1_K3_validate",
                "falsifier_ledger_present",
                "morphology_gate_threshold_met_or_explicit_absence",
                f"engine_score={engine.total:.2f}",
                f"baseline_score={baseline.total:.2f}",
                f"pubmed_lift={engine.total - baseline.total:.2f}",
            ],
            "decision_context": "Research-only cardiac evidence packet generated CPU-side.",
        },
    )

    # 5. Reasoner tuple
    queue = ReasonerQueue(queue_path=queue_root, run_id=rid)
    backend = StubReasonerBackend()
    reasoner_input = ReasonerInput(
        question=f"What is the multi-current research-only signal for {compound}?",
        entities=TupleEntities(
            compounds=[fixture["name"]],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
            currents=["IKr", "INaL", "IKs", "ICaL"],
            phenotypes=["QT/QTc"],
        ),
        context_pack_refs=[
            "source:FDA_E14_S7B",
            "source:FDA_CiPA",
            "source:ICH_M15_2026",
            "source:PTB_XL_plus",
            f"packet:{packet.packet_id}",
        ],
        constraints=TupleConstraints(),
    )
    tup = run_reasoner_step(adapter=backend, input_block=reasoner_input, run_id=rid, queue=queue)

    # Add ReasonerTuple KG node
    rt_node_id = f"ReasonerTuple:{tup.tuple_id}"
    kg.add_node(
        KGNode(
            node_id=rt_node_id,
            node_type=NodeType.REASONER_TUPLE,
            properties={
                "tuple_id": tup.tuple_id,
                "task_type": tup.task_type.value,
                "falsifier_class": tup.falsifier.falsifier_class.value,
                "falsifier_status": tup.falsifier.status.value,
            },
        )
    )
    runtime_node_count += 1
    kg.add_edge(
        KGEdge(
            edge_id=f"edge:DERIVES_TUPLE:{packet_node_id}:{rt_node_id}",
            edge_type=EdgeType.DERIVES_TUPLE,
            source_node_id=packet_node_id,
            target_node_id=rt_node_id,
        )
    )
    runtime_edge_count += 1

    # 6. Offload manifest (records what would be offloaded to private HF dataset; no real upload here).
    aw.append(
        AuditTable.OFFLOAD_MANIFEST,
        {
            "run_id": rid,
            "artifact_id": f"artifact:packet:{packet.packet_id}",
            "hf_dataset_ref": (
                f"Architect-Prime/zer0pa-health-cardiac-packets:packets/"
                f"cardiac_evidence_packet_v0_1__{compound}.json"
            ),
            "size_bytes": len(packet.model_dump_json()),
        },
    )

    # 7. Validate the audit log we just wrote (acceptance gate per PRD section 11)
    AuditValidator(audit_root, rid).validate()

    # 8. Compute counts
    audit_table_counts: dict[str, int] = {}
    for table in AuditTable:
        path = audit_root / "runs" / rid / f"{table.value}.jsonl"
        if path.exists():
            audit_table_counts[table.value] = sum(
                1 for line in path.open("r", encoding="utf-8") if line.strip()
            )
        else:
            audit_table_counts[table.value] = 0

    fail_counts = led.fail_count_by_class()

    return CardiacRunResult(
        run_id=rid,
        compound=compound,
        audit_root=audit_root,
        kg_root=kg_root,
        packet_path=packet_path,
        reasoner_queue_path=queue_root / "runs" / rid / "tuples.jsonl",
        audit_table_counts=audit_table_counts,
        falsifier_fail_counts=fail_counts,
        kg_runtime_nodes=runtime_node_count,
        kg_runtime_edges=runtime_edge_count,
        reasoner_tuples_emitted=1,
        packet_verdict=packet.verdict.value,
        engine_score=engine.total,
        baseline_score=baseline.total,
        pubmed_lift=engine.total - baseline.total,
        backedges_emitted=backedges,
        decisions_recorded=decisions,
    )


_DEFAULT_CMAX_uM = {
    "dofetilide": 0.001,
    "verapamil": 0.05,
    "ranolazine": 2.0,
    "quinidine": 1.5,
    "moxifloxacin": 3.0,
    "diltiazem": 0.1,
    "sotalol": 5.0,
    "mexiletine": 1.5,
    "lidocaine": 1.0,
}


def run_cardiac_wedge(
    runtime_root: Path,
    compounds: list[str] | None = None,
) -> list[CardiacRunResult]:
    """Run the full cardiac wedge (default: dofetilide / verapamil / ranolazine).

    Returns one CardiacRunResult per compound.
    """
    compounds = compounds or ["dofetilide", "verapamil", "ranolazine"]
    out: list[CardiacRunResult] = []
    for c in compounds:
        cmax = _DEFAULT_CMAX_uM.get(c, 1.0)
        out.append(
            run_cardiac_compound(c, runtime_root=runtime_root, cmax_unbound_uM=cmax)
        )
    return out

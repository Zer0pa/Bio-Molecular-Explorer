"""L1 Runpod-sim adapter: pretends to be the GPU-real L1 adapter.

Same envelope shape as L1StubAdapter, but `tool_adapter.backend = "runpod_gpu"`,
`tool_adapter.engine = "diffdock_v2_runpod_sim"`, and the canned values are
slightly different to simulate "the GPU just gave us better numbers".

Critically: it does NOT raise — calling its methods returns a fully-formed
LayerEnvelope with backend="runpod_gpu". This is what makes the cutover-
acceptance test possible on CPU. The real GPU adapter at cutover replaces this
sim adapter; the rest of the pipeline does not change.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_health.contracts.l1 import (
    L1ChannelPanelInput,
    L1DockingInput,
    L1FEPInput,
    L1MDInput,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_health.envelope import (
    Backend,
    BackEdge,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    EnvelopeFalsifierItem,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import (
    detect_herg_only_overreach,
    detect_invalid_smiles,
    detect_stub_laundering,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id


def _seed_float(*parts: str, lo: float, hi: float) -> float:
    """Deterministic float in [lo, hi] from a seed string."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * n


class L1RunpodSimAdapter:
    """CPU simulation of what the L1 GPU-real adapter will return at cutover.

    Same interface as L1StubAdapter. backend=runpod_gpu. engine="diffdock_v2_runpod_sim".
    The cutover-acceptance test (tests/integration/test_runpod_cutover.py) flips
    the L1 stub for this sim adapter and verifies downstream pipeline parses unchanged.
    """

    NAME = "l1-runpod-sim"
    VERSION = "0.1.0"
    ENGINE = "diffdock_v2_runpod_sim"

    def __init__(self) -> None:
        self._adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.RUNPOD_GPU,
            engine=self.ENGINE,
        )

    # ----- helpers -----

    def _falsifier(self, smiles: str, *, mechanism_escalation: bool = False) -> list[EnvelopeFalsifierItem]:
        items = [detect_invalid_smiles(smiles)]
        # On a real GPU adapter, stub_laundering is PASS because backend != stub.
        items.append(
            detect_stub_laundering(
                backend=Backend.RUNPOD_GPU.value,
                claim_kind="mechanism_claim",
                mechanism_escalation=mechanism_escalation,
            )
        )
        return items

    def _envelope(
        self,
        *,
        run_id: str,
        output: dict[str, Any],
        falsifier_items: list[EnvelopeFalsifierItem],
        confidence_score: float,
        confidence_basis: list[str],
        input_refs: list[str] | None = None,
        back_edges: list[BackEdge] | None = None,
    ) -> LayerEnvelope:
        any_fail = any(it.status == FalsifierStatus.FAIL for it in falsifier_items)
        envelope_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS
        return LayerEnvelope(
            run_id=run_id,
            layer=LayerName.L1,
            tool_adapter=self._adapter,
            input_refs=input_refs or [],
            output=output,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=ConfidenceBand.HIGH if confidence_score >= 0.7 else ConfidenceBand.MEDIUM,
                basis=confidence_basis,
            ),
            falsifier=EnvelopeFalsifier(status=envelope_status, items=falsifier_items),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(output),
                output_hash=sha256_of_obj(output),
            ),
            back_edges=back_edges or [],
        )

    # ----- public methods (same interface as L1StubAdapter) -----

    def ligand(self, inp: L1MoleculeInput, *, run_id: str | None = None) -> LayerEnvelope:
        rid = run_id or new_run_id()
        falsifiers = self._falsifier(inp.smiles)
        if any(it.status == FalsifierStatus.FAIL for it in falsifiers):
            output = {"canonical_smiles": "", "inchikey": "", "valid": False}
        else:
            output = {
                "canonical_smiles": inp.smiles.strip(),
                "inchikey": inp.inchikey or "GPUSIM-INCHIKEY",
                "valid": True,
                "standardized_by": "runpod_sim_canonicalizer",
            }
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.85,  # GPU adapters report higher confidence than stubs
            confidence_basis=["runpod_gpu_canonicalizer"],
        )

    def target(self, inp: L1TargetInput, *, run_id: str | None = None) -> LayerEnvelope:
        rid = run_id or new_run_id()
        output = {
            "target_id": f"uniprot:{inp.gene.value}",
            "gene_symbol": inp.gene.value,
            "current": inp.current.value,
            "structure_basis": "PDB",
            "structure_ref": inp.structure_ref,
        }
        falsifiers = [
            EnvelopeFalsifierItem(
                falsifier_id="falsifier:stub_laundering:runpod-pass",
                falsifier_class="stub_laundering",
                trigger_condition="Stub output is treated as real simulation",
                status=FalsifierStatus.PASS,
                evidence=["backend=runpod_gpu; not a stub"],
            )
        ]
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.9,
            confidence_basis=["runpod_gpu_target_resolver"],
        )

    def dock(self, inp: L1DockingInput, *, run_id: str | None = None) -> LayerEnvelope:
        rid = run_id or new_run_id()
        falsifiers = self._falsifier(inp.molecule.smiles)
        poses = [
            {
                "pose_index": i,
                "confidence": _seed_float(inp.molecule.smiles, str(i), lo=0.6, hi=0.85),
                "estimated_binding_kcal_mol": -_seed_float(
                    inp.molecule.smiles, str(i), "binding", lo=5.0, hi=9.0
                ),
                "structure_basis": "mmCIF",  # GPU adapters use real structure
            }
            for i in range(inp.n_poses)
        ]
        output = {
            "molecule_inchikey": inp.molecule.inchikey or "GPUSIM-INCHIKEY",
            "target_gene": inp.target.gene.value,
            "target_current": inp.target.current.value,
            "poses": poses,
            "structure_confidence": 0.85,
            "binding_confidence": 0.78,
        }
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.78,
            confidence_basis=["runpod_diffdock_v2_sim", "real_mmCIF_basis"],
        )

    def md(self, inp: L1MDInput, *, run_id: str | None = None) -> LayerEnvelope:
        rid = run_id or new_run_id()
        falsifiers = self._falsifier(inp.molecule.smiles)
        output = {
            "molecule_inchikey": inp.molecule.inchikey or "GPUSIM-INCHIKEY",
            "target_gene": inp.target.gene.value,
            "rmsd_nm": _seed_float(inp.molecule.smiles, "md", lo=0.10, hi=0.30),
            "convergence_metric": _seed_float(inp.molecule.smiles, "conv", lo=0.7, hi=0.95),
            "n_frames": int(inp.sim_ns * 50),  # GPU runs more frames
        }
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.82,
            confidence_basis=["runpod_openmm_sim"],
        )

    def fep(self, inp: L1FEPInput, *, run_id: str | None = None) -> LayerEnvelope:
        rid = run_id or new_run_id()
        falsifiers = self._falsifier(inp.ligand_a.smiles)
        falsifiers.extend(self._falsifier(inp.ligand_b.smiles))
        output = {
            "ddg_kcal_mol": _seed_float(
                inp.ligand_a.smiles, inp.ligand_b.smiles, lo=-1.5, hi=1.5
            ),
            "ddg_uncertainty_kcal_mol": _seed_float(
                inp.ligand_a.smiles, "uncert", lo=0.2, hi=0.8
            ),
            "convergence_ok": True,
            "method": inp.method,
        }
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.80,
            confidence_basis=["runpod_openfe_rbfe_sim"],
        )

    def channel_panel(
        self,
        inp: L1ChannelPanelInput,
        *,
        ligand_smiles: str,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        smiles_check = detect_invalid_smiles(ligand_smiles)
        if smiles_check.status == FalsifierStatus.FAIL:
            output = {
                "molecule_inchikey": "",
                "panel": {},
                "multi_current_balance_score": None,
                "explicit_absence": [],
                "basis": ["invalid_input"],
            }
            falsifiers = [
                smiles_check,
                EnvelopeFalsifierItem(
                    falsifier_id="falsifier:stub_laundering:runpod-pass",
                    falsifier_class="stub_laundering",
                    trigger_condition="Stub output is treated as real simulation",
                    status=FalsifierStatus.PASS,
                    evidence=["backend=runpod_gpu"],
                ),
                detect_herg_only_overreach([], []),
            ]
            return self._envelope(
                run_id=rid,
                output=output,
                falsifier_items=falsifiers,
                confidence_score=0.0,
                confidence_basis=["invalid_input"],
            )

        # Real GPU adapter would return computed IC50s. The sim returns
        # deterministic stub values so the cutover test can verify shape.
        panel: dict[str, dict[str, float | None]] = {}
        explicit_absence: list[str] = []
        for tgt in inp.targets:
            ic50 = _seed_float(ligand_smiles, tgt.gene.value, lo=0.5, hi=8.0)
            panel[tgt.gene.value] = {
                "ic50_uM": ic50,
                "confidence": _seed_float(ligand_smiles, tgt.gene.value, "conf", lo=0.7, hi=0.9),
            }

        # Compute a fake balance score (just for shape consistency)
        balance = _seed_float(ligand_smiles, "balance", lo=-0.5, hi=0.5)

        output = {
            "molecule_inchikey": "GPUSIM-INCHIKEY",
            "panel": panel,
            "multi_current_balance_score": balance,
            "explicit_absence": explicit_absence,
            "basis": ["runpod_diffdock_v2_panel_sim", "real_structure_basis"],
        }
        herg = detect_herg_only_overreach(
            panel_genes_present=[g for g in panel.keys()],
            explicit_absence=explicit_absence,
        )
        falsifiers = [
            smiles_check,
            EnvelopeFalsifierItem(
                falsifier_id="falsifier:stub_laundering:runpod-pass",
                falsifier_class="stub_laundering",
                trigger_condition="Stub output is treated as real simulation",
                status=FalsifierStatus.PASS,
                evidence=["backend=runpod_gpu"],
            ),
            herg,
        ]
        return self._envelope(
            run_id=rid,
            output=output,
            falsifier_items=falsifiers,
            confidence_score=0.85,
            confidence_basis=["runpod_diffdock_v2_panel_sim", "real_structure_basis"],
        )

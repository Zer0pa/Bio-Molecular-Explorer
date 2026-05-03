"""P1.Structure Runpod-sim adapter.

Pretends to be the GPU-real OpenFold3 adapter at envelope level:
- backend = runpod_gpu
- engine = "openfold3_runpod_sim"
- structure_source_tag = "openfold3"  (NOT "stub")
- openfold3_run_id = f"runpod_sim:run:<rid>"
- structure confidence 0.85+, mean_plddt 80-95
- stub_laundering PASSES (backend != stub)
- Same envelope shape as P1StructureStubAdapter for plug-replaceability.
"""

from __future__ import annotations

import hashlib

from zer0pa_biomolecular_explorer.envelope import (
    Backend,
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
from zer0pa_biomolecular_explorer.falsifiers.detectors import (
    detect_alphafold_d_leakage,
    detect_clinical_overclaim,
    detect_stub_laundering,
    detect_structure_confidence_below_threshold,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_structure import (
    P1BindingPocket,
    P1StructureDossier,
    P1StructureInput,
    P1StructureOutput,
)

_ADAPTER_NAME = "p1-structure-runpod-sim"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "openfold3_runpod_sim"
_SEED_PREFIX = "p1structure_runpod_sim"


def _seed_float(*parts: str, lo: float, hi: float) -> float:
    joined = "|".join(str(p) for p in parts)
    h = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * n


def _seed_int(*parts: str, lo: int, hi: int) -> int:
    joined = "|".join(str(p) for p in parts)
    h = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    n = int(h[8:16], 16) % (hi - lo + 1)
    return lo + n


class P1StructureRunpodSimAdapter:
    """CPU simulation of what the P1.Structure GPU-real adapter will return at cutover.

    Same interface as P1StructureStubAdapter. backend=runpod_gpu.
    engine="openfold3_runpod_sim". structure_source_tag="openfold3".
    The cutover-acceptance test swaps the stub for this sim adapter and
    verifies the downstream pipeline parses unchanged.
    """

    NAME = _ADAPTER_NAME
    VERSION = _ADAPTER_VERSION
    ENGINE = _ENGINE

    def __init__(self) -> None:
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.RUNPOD_GPU,
            engine=self.ENGINE,
        )

    def process(
        self,
        input: P1StructureInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        openfold3_run_id = f"runpod_sim:run:{rid}"

        # GPU adapter returns higher confidence pLDDT values
        mean_plddt = _seed_float(_SEED_PREFIX, input.target_id, "plddt", lo=80.0, hi=95.0)
        bs_plddt = _seed_float(_SEED_PREFIX, input.target_id, "bs_plddt", lo=80.0, hi=95.0)

        n_residues = _seed_int(_SEED_PREFIX, input.target_id, "n_res", lo=8, hi=12)
        residues = list(range(1, n_residues + 1))
        labels = [f"R{r}" for r in residues]
        volume = _seed_float(_SEED_PREFIX, input.target_id, "volume", lo=350.0, hi=450.0)

        pocket = P1BindingPocket(
            pocket_id=f"pocket:{input.target_id}:{_SEED_PREFIX}",
            binding_site_residues=residues,
            binding_site_residue_labels=labels,
            pocket_volume_angstrom3=volume,
            pocket_label="openfold3_inner_cavity",
        )

        dossier = P1StructureDossier(
            target_id=input.target_id,
            gene_symbol=input.gene_symbol,
            structure_source_tag="openfold3",
            structure_ref=f"openfold3:{input.target_id}:{openfold3_run_id}",
            uniprot_af_id=None,
            openfold3_run_id=openfold3_run_id,
            pocket=pocket,
            mean_plddt=mean_plddt,
            binding_site_mean_plddt=bs_plddt,
        )

        # Falsifiers
        falsifier_items: list[EnvelopeFalsifierItem] = []

        # 1. AlphaFold D leakage — PASS (structure_source_tag="openfold3", openfold3_run_id set)
        falsifier_items.append(
            detect_alphafold_d_leakage(
                structure_source_tag=dossier.structure_source_tag,
                uniprot_af_id=dossier.uniprot_af_id,
                openfold3_run_id=dossier.openfold3_run_id,
            )
        )

        # 2. Structure confidence below threshold
        falsifier_items.append(
            detect_structure_confidence_below_threshold(
                binding_site_mean_plddt=dossier.binding_site_mean_plddt,
                structure_source="openfold3",
            )
        )

        # 3. Stub laundering — PASS because backend != stub
        falsifier_items.append(
            detect_stub_laundering(
                backend=Backend.RUNPOD_GPU.value,
                claim_kind="mechanism_claim",
                mechanism_escalation=False,
            )
        )

        # 4. Clinical overclaim
        probe_text = f"{dossier.structure_ref} {dossier.gene_symbol} {dossier.target_id}"
        falsifier_items.append(detect_clinical_overclaim(probe_text))

        any_fail = any(
            it.status in (FalsifierStatus.FAIL, "fail") for it in falsifier_items
        )
        envelope_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        output_dict = P1StructureOutput(dossier=dossier).model_dump(mode="json")
        confidence_score = _seed_float(_SEED_PREFIX, input.target_id, "conf", lo=0.85, hi=0.95)

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_STRUCTURE,
            tool_adapter=self._tool_adapter,
            input_refs=[f"target:{dossier.target_id}"],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=ConfidenceBand.HIGH,
                basis=["openfold3_runpod_sim", "gpu_recompute"],
            ),
            falsifier=EnvelopeFalsifier(status=envelope_status, items=falsifier_items),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input.model_dump(mode="json")),
                output_hash=sha256_of_obj(output_dict),
            ),
            back_edges=[],
        )

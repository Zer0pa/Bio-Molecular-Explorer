"""P1.Structure stub adapter — backend=stub, deterministic canned values.

Adapter discipline
------------------
- process(input, *, run_id=None) -> LayerEnvelope
- structure_source_tag = "stub" (NOT "openfold3" — that is the runpod_sim)
- openfold3_run_id = f"stub:run:<run_id>" — indicates a stub recompute, NOT None
- uniprot_af_id = None  (we do NOT use AF DB in stub; using AF DB without
  an OpenFold3 recompute provenance would trip detect_alphafold_d_leakage)
- AlphaFold D leakage trip case: if caller supplies pdb_ref_hint matching
  ^AF-[A-Z0-9]+-F\\d+$ AND we set uniprot_af_id to that value AND
  openfold3_run_id=None, the detector fires. The adapter's normal path
  does NOT do this; a dedicated internal method `_process_af_db_leak_case`
  enables the test scenario.
- Pocket: deterministic seeded values, residues 1-12, volume 350-450 Å³
- mean_plddt: deterministic in [70.0, 92.0]
- binding_site_mean_plddt: deterministic in [65.0, 88.0]
- Falsifiers run: ALPHAFOLD_D_LEAKAGE (PASS), STRUCTURE_CONFIDENCE_BELOW_THRESHOLD,
  STUB_LAUNDERING (PASS), CLINICAL_OVERCLAIM (PASS)
"""

from __future__ import annotations

import hashlib
from typing import Any

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

_ADAPTER_NAME = "p1-structure-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_canned"

# Seed prefix used for deterministic hashing — separate from ToyAdapter
_SEED_PREFIX = "p1structure_stub"


def _seed_float(*parts: str, lo: float, hi: float) -> float:
    """Deterministic float in [lo, hi] derived from seed parts via sha256."""
    joined = "|".join(str(p) for p in parts)
    h = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * n


def _seed_int(*parts: str, lo: int, hi: int) -> int:
    """Deterministic int in [lo, hi] (inclusive) derived from seed parts."""
    joined = "|".join(str(p) for p in parts)
    h = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    n = int(h[8:16], 16) % (hi - lo + 1)
    return lo + n


def _build_pocket(target_id: str, seed_prefix: str) -> P1BindingPocket:
    """Build a deterministic P1BindingPocket from target_id."""
    pocket_id = f"pocket:{target_id}:{seed_prefix}"
    n_residues = _seed_int(seed_prefix, target_id, "n_res", lo=8, hi=12)
    residues = list(range(1, n_residues + 1))
    labels = [f"R{r}" for r in residues]
    volume = _seed_float(seed_prefix, target_id, "volume", lo=350.0, hi=450.0)
    return P1BindingPocket(
        pocket_id=pocket_id,
        binding_site_residues=residues,
        binding_site_residue_labels=labels,
        pocket_volume_angstrom3=volume,
        pocket_label="stub_inner_cavity",
    )


def _build_dossier(
    inp: P1StructureInput,
    rid: str,
    *,
    seed_prefix: str,
    structure_source_tag: str = "stub",
    uniprot_af_id: str | None = None,
    openfold3_run_id: str | None = None,
    structure_ref: str | None = None,
) -> P1StructureDossier:
    mean_plddt = _seed_float(seed_prefix, inp.target_id, "plddt", lo=70.0, hi=92.0)
    bs_plddt = _seed_float(seed_prefix, inp.target_id, "bs_plddt", lo=65.0, hi=88.0)
    _openfold3_run_id = openfold3_run_id if openfold3_run_id is not None else f"stub:run:{rid}"
    _structure_ref = structure_ref or f"stub:openfold3:{inp.target_id}"
    pocket = _build_pocket(inp.target_id, seed_prefix)
    return P1StructureDossier(
        target_id=inp.target_id,
        gene_symbol=inp.gene_symbol,
        structure_source_tag=structure_source_tag,  # type: ignore[arg-type]
        structure_ref=_structure_ref,
        uniprot_af_id=uniprot_af_id,
        openfold3_run_id=_openfold3_run_id,
        pocket=pocket,
        mean_plddt=mean_plddt,
        binding_site_mean_plddt=bs_plddt,
    )


def _run_falsifiers(
    dossier: P1StructureDossier,
    *,
    backend: str,
    claim_kind: str = "mechanism_claim",
    mechanism_escalation: bool = False,
    structure_source: str = "stub",
) -> list[EnvelopeFalsifierItem]:
    items: list[EnvelopeFalsifierItem] = []

    # 1. AlphaFold D leakage — PASS for normal stub (openfold3_run_id is set)
    items.append(
        detect_alphafold_d_leakage(
            structure_source_tag=dossier.structure_source_tag,
            uniprot_af_id=dossier.uniprot_af_id,
            openfold3_run_id=dossier.openfold3_run_id,
        )
    )

    # 2. Structure confidence below threshold
    items.append(
        detect_structure_confidence_below_threshold(
            binding_site_mean_plddt=dossier.binding_site_mean_plddt,
            structure_source=structure_source,
        )
    )

    # 3. Stub laundering
    items.append(
        detect_stub_laundering(
            backend=backend,
            claim_kind=claim_kind,
            mechanism_escalation=mechanism_escalation,
        )
    )

    # 4. Clinical overclaim — check structure_ref + gene_symbol string
    probe_text = f"{dossier.structure_ref} {dossier.gene_symbol} {dossier.target_id}"
    items.append(detect_clinical_overclaim(probe_text))

    return items


def _build_envelope(
    *,
    run_id: str,
    dossier: P1StructureDossier,
    falsifier_items: list[EnvelopeFalsifierItem],
    tool_adapter: ToolAdapter,
    confidence_score: float,
    confidence_basis: list[str],
    input_obj: Any,
    output_obj: Any,
) -> LayerEnvelope:
    any_fail = any(it.status in (FalsifierStatus.FAIL, "fail") for it in falsifier_items)
    envelope_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS
    output_dict = P1StructureOutput(dossier=dossier).model_dump(mode="json")
    return LayerEnvelope(
        run_id=run_id,
        layer=LayerName.P1_STRUCTURE,
        tool_adapter=tool_adapter,
        input_refs=[f"target:{dossier.target_id}"],
        output=output_dict,
        confidence=EnvelopeConfidence(
            score=confidence_score,
            band=ConfidenceBand.HIGH if confidence_score >= 0.7 else ConfidenceBand.MEDIUM,
            basis=confidence_basis,
        ),
        falsifier=EnvelopeFalsifier(status=envelope_status, items=falsifier_items),
        audit=EnvelopeAudit(
            audit_record_id=audit_id(),
            input_hash=sha256_of_obj(input_obj),
            output_hash=sha256_of_obj(output_dict),
        ),
        back_edges=[],
    )


class P1StructureStubAdapter:
    """P1.Structure stub adapter.

    Returns deterministic canned structure data. backend=stub.
    structure_source_tag="stub" (NOT "openfold3").
    openfold3_run_id is always set to f"stub:run:<rid>" on the normal path
    so detect_alphafold_d_leakage always PASSES.
    """

    NAME = _ADAPTER_NAME
    VERSION = _ADAPTER_VERSION
    ENGINE = _ENGINE

    def __init__(self) -> None:
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.STUB,
            engine=self.ENGINE,
        )

    def process(
        self,
        input: P1StructureInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Normal path: structure_source_tag='stub', openfold3_run_id set, AF leakage PASSES."""
        rid = run_id or new_run_id()
        dossier = _build_dossier(
            input,
            rid,
            seed_prefix=_SEED_PREFIX,
            structure_source_tag="stub",
            uniprot_af_id=None,
            openfold3_run_id=None,  # will be auto-set to f"stub:run:{rid}"
        )
        falsifier_items = _run_falsifiers(
            dossier,
            backend=Backend.STUB.value,
            mechanism_escalation=False,
            structure_source="stub",
        )
        return _build_envelope(
            run_id=rid,
            dossier=dossier,
            falsifier_items=falsifier_items,
            tool_adapter=self._tool_adapter,
            confidence_score=0.6,
            confidence_basis=["stub_canned_structure"],
            input_obj=input.model_dump(mode="json"),
            output_obj=dossier.model_dump(mode="json"),
        )

    def _process_af_db_leak_case(
        self,
        input: P1StructureInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Test-only path: simulates a misconfigured adapter that:
        - sets structure_source_tag='alphafold_db_precomputed'
        - sets uniprot_af_id from pdb_ref_hint (if AF pattern matches)
        - leaves openfold3_run_id=None
        This MUST trigger detect_alphafold_d_leakage FAIL.
        """
        rid = run_id or new_run_id()
        pdb_hint = input.pdb_ref_hint or ""
        import re
        af_pattern = re.compile(r"^AF-[A-Z0-9]+-F\d+$")
        if af_pattern.match(pdb_hint):
            uniprot_af_id = pdb_hint
        else:
            uniprot_af_id = None

        dossier = _build_dossier(
            input,
            rid,
            seed_prefix=_SEED_PREFIX,
            structure_source_tag="alphafold_db_precomputed",
            uniprot_af_id=uniprot_af_id,
            openfold3_run_id=None,  # intentionally None — triggers leakage detector
            structure_ref=f"af_db:{uniprot_af_id or pdb_hint}",
        )
        # override openfold3_run_id to ensure None (already set above via _build_dossier
        # but dossier was built with openfold3_run_id=None, however _build_dossier
        # auto-fills it with "stub:run:{rid}" if None — we must override)
        dossier = dossier.model_copy(update={"openfold3_run_id": None})
        falsifier_items = _run_falsifiers(
            dossier,
            backend=Backend.STUB.value,
            mechanism_escalation=False,
            structure_source="alphafold_db_precomputed",
        )
        return _build_envelope(
            run_id=rid,
            dossier=dossier,
            falsifier_items=falsifier_items,
            tool_adapter=self._tool_adapter,
            confidence_score=0.6,
            confidence_basis=["stub_canned_structure"],
            input_obj=input.model_dump(mode="json"),
            output_obj=dossier.model_dump(mode="json"),
        )

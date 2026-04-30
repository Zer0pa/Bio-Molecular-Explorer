"""P1.Generate stub adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Generates a deterministic stub library of candidate SMILES from a fixed 20-SMILES pool.
Runs PRETRAINED_HALLUCINATION, IP_CHEMSPACE_DRIFT, NOVELTY_WITHOUT_TRACTABILITY,
STUB_LAUNDERING, and CLINICAL_OVERCLAIM falsifiers per candidate / per envelope.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_health.envelope import (
    BackEdge,
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
from zer0pa_health.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_ip_chemspace_drift,
    detect_novelty_without_tractability,
    detect_pretrained_hallucination,
    detect_stub_laundering,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.pathway1.contracts.p1_generate import (
    P1GenerateInput,
    P1GenerateOutput,
    P1GeneratedCandidate,
)

# ── Deterministic 20-SMILES pool (all valid, drug-like molecules) ──────────────
_SMILES_POOL: tuple[str, ...] = (
    "CC(=O)Nc1ccc(O)cc1",                                   # paracetamol
    "CC(C)Cc1ccc(C(C)C(=O)O)cc1",                          # ibuprofen-like
    "CN(C)CCCC1(c2ccc(F)cc2)OCc2cc(C#N)ccc21",             # citalopram-like
    "CC1=CC2=C(C=C1C)N(CC(O)CO)C3=CC(=O)NC(=O)C3=N2",    # riboflavin-like
    "COc1ccc2c(c1)cc(CC(=O)O)n2C",                         # indomethacin-like
    "Cc1ccc(-c2cc(C(F)(F)F)nn2-c2ccc(S(N)(=O)=O)cc2)cc1", # celecoxib-like
    "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C",                # testosterone-like
    "O=C(O)c1ccccc1OC(=O)C",                               # aspirin
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",                        # caffeine
    "CC(=O)OC1=CC=CC=C1C(=O)O",                            # aspirin v2
    "c1ccc2c(c1)ccc1ccccc12",                              # anthracene
    "O=C(O)CCC(=O)O",                                      # succinic acid
    "CC(N)Cc1ccccc1",                                       # amphetamine-like
    "O=C(Nc1ccccc1)c1ccccc1",                              # benzanilide
    "CC(=O)c1ccc(N)cc1",                                    # 4-aminoacetophenone
    "Nc1ccc(S(=O)(=O)N)cc1",                               # sulfanilamide
    "OC(=O)c1ccc(N)cc1",                                    # 4-aminobenzoic acid
    "CC(O)c1ccccc1",                                        # 1-phenylethan-1-ol
    "O=C(O)CC(O)(CC(=O)O)C(=O)O",                         # citric acid
    "CC1=CC(=O)c2ccccc2C1=O",                              # 2-methylnaphthaquinone
)

# Deterministic stub Tanimoto values for IP_CHEMSPACE_DRIFT per SMILES index
# (lo = below threshold 0.95 → PASS; hi = at/above → FAIL)
_ZINC22_TANIMOTO: tuple[float, ...] = (
    0.10, 0.22, 0.35, 0.45, 0.55,
    0.60, 0.65, 0.70, 0.75, 0.80,
    0.82, 0.84, 0.86, 0.88, 0.90,
    0.91, 0.92, 0.93, 0.94, 0.80,
)

# Deterministic tractability stubs (max_chembl_tanimoto, sa_score, askcos_step_count)
_TRACTABILITY: tuple[tuple[float, float, int | None], ...] = (
    (0.85, 2.1, 3),  # PASS: known scaffold, easy synth
    (0.80, 2.5, 4),
    (0.70, 3.0, 5),
    (0.60, 3.5, 4),
    (0.50, 4.0, 6),
    (0.45, 4.2, 5),
    (0.40, 4.4, 7),
    (0.38, 4.6, 8),  # FAIL: novel + hard synth
    (0.35, 5.0, 9),  # FAIL: novel + hard synth + too many steps
    (0.30, 3.0, 3),  # FAIL: very novel but easy synth (sa PASS, steps PASS) → PASS overall
    (0.82, 2.0, 2),
    (0.78, 2.2, 3),
    (0.72, 2.8, 4),
    (0.68, 3.1, 5),
    (0.62, 3.4, 4),
    (0.55, 4.0, 6),
    (0.48, 4.3, 7),
    (0.42, 4.4, 6),
    (0.39, 5.1, 5),  # FAIL: novel + sa too high
    (0.88, 2.5, 3),
)

_CANDIDATE_CONFIDENCE: tuple[float, ...] = (
    0.72, 0.68, 0.65, 0.63, 0.60,
    0.58, 0.57, 0.55, 0.53, 0.50,
    0.71, 0.66, 0.64, 0.62, 0.59,
    0.57, 0.56, 0.54, 0.52, 0.70,
)

_ADAPTER_NAME = "p1-generate-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_canned_smiles_pool"

_POOL_SIZE = len(_SMILES_POOL)
_MAX_LIBRARY_SIZE = 50  # cap for test/stub mode


def _candidate_id(seed: str, idx: int) -> str:
    return f"P1-GEN-{seed}-{idx:04d}"


def _short_seed(target_id: str, mode: str) -> str:
    """Deterministic short seed from target+mode."""
    raw = f"{target_id}|{mode}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


class P1GenerateStubAdapter:
    """Deterministic stub adapter for P1.Generate.

    - Rotates a fixed 20-SMILES pool to fill `library_size` (capped at 50).
    - Runs PRETRAINED_HALLUCINATION per candidate; failing candidates are dropped.
    - Runs IP_CHEMSPACE_DRIFT per candidate using deterministic stub Tanimoto.
    - Runs NOVELTY_WITHOUT_TRACTABILITY on each candidate using deterministic stubs.
    - Runs STUB_LAUNDERING and CLINICAL_OVERCLAIM at envelope level.
    """

    NAME = _ADAPTER_NAME
    VERSION = _ADAPTER_VERSION
    ENGINE = _ENGINE

    def __init__(self, *, force_ip_drift_fail: bool = False) -> None:
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.STUB,
            engine=self.ENGINE,
        )
        # test-only flag to force IP_CHEMSPACE_DRIFT FAIL on all candidates
        self._force_ip_drift_fail = force_ip_drift_fail

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        inp: P1GenerateInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        seed = _short_seed(inp.target_id, inp.mode)

        effective_size = min(inp.library_size, _MAX_LIBRARY_SIZE)
        candidates: list[P1GeneratedCandidate] = []
        dropped_count = 0
        all_falsifier_items: list[EnvelopeFalsifierItem] = []

        for idx in range(effective_size):
            pool_idx = idx % _POOL_SIZE
            smiles = self._pool()[pool_idx]

            # Inject iron atom for test-only forced hallucination
            smiles = self._maybe_inject_hallucination(smiles, idx, seed)

            hall_item = detect_pretrained_hallucination(smiles, inp.mode)
            all_falsifier_items.append(hall_item)
            if hall_item.status == FalsifierStatus.FAIL:
                dropped_count += 1
                continue

            # IP_CHEMSPACE_DRIFT
            tanimoto = 0.97 if self._force_ip_drift_fail else self._zinc22_tanimoto_for_pool_idx(pool_idx)
            ip_item = detect_ip_chemspace_drift(
                candidate_smiles=smiles,
                best_zinc22_tanimoto=tanimoto,
                zinc22_catalogue_id=f"ZINC-{pool_idx:06d}",
                purchase_agreement_ref=None,
            )
            all_falsifier_items.append(ip_item)

            # NOVELTY_WITHOUT_TRACTABILITY
            max_chbl_tan, sa_sc, askcos_steps = _TRACTABILITY[pool_idx]
            nov_item = detect_novelty_without_tractability(
                max_chembl_tanimoto=max_chbl_tan,
                sa_score=sa_sc,
                askcos_step_count=askcos_steps,
            )
            all_falsifier_items.append(nov_item)

            parent_scaffold = inp.seed_scaffold_smiles if inp.mode == "scaffold_hop" else None

            candidates.append(
                P1GeneratedCandidate(
                    candidate_id=_candidate_id(seed, idx),
                    smiles=smiles,
                    generation_method=inp.mode,
                    parent_scaffold=parent_scaffold,
                    confidence=_CANDIDATE_CONFIDENCE[pool_idx],
                )
            )

        # Envelope-level falsifiers
        stub_launder = detect_stub_laundering(
            backend=Backend.STUB.value,
            claim_kind="candidate_library",
            mechanism_escalation=False,
        )
        clinical = detect_clinical_overclaim("")
        all_falsifier_items.extend([stub_launder, clinical])

        output_obj = P1GenerateOutput(
            target_id=inp.target_id,
            library_size_actual=len(candidates),
            candidates=candidates,
            mode_used=inp.mode,
            backend_used=self._backend_value(),
        )
        output_dict = output_obj.model_dump()
        output_dict["dropped_count"] = dropped_count

        any_fail = any(it.status == FalsifierStatus.FAIL for it in all_falsifier_items)
        back_edges: list[BackEdge] = []
        if any_fail:
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.P1_GENERATE,
                    reason="One or more falsifiers FAILED; dropped candidates recorded.",
                    proposed_constraint={"dropped_count": dropped_count},
                )
            )

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_GENERATE,
            tool_adapter=self._tool_adapter,
            input_refs=[inp.target_id, inp.structure_ref, inp.pocket_id],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=0.55,
                band=ConfidenceBand.LOW,
                basis=["stub_canned_smiles_pool"],
            ),
            falsifier=EnvelopeFalsifier(
                status=FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS,
                items=all_falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(inp.model_dump()),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=["stub_smiles_pool_v1"],
            ),
            back_edges=back_edges,
        )

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _pool(self) -> tuple[str, ...]:
        """Return the SMILES pool. Subclasses may override to rotate order."""
        return _SMILES_POOL

    def _backend_value(self) -> str:
        """Return the backend string for output.backend_used. Subclasses may override."""
        return Backend.STUB.value

    def _zinc22_tanimoto_for_pool_idx(self, pool_idx: int) -> float:
        """Return the stub Tanimoto for a given pool index. Subclasses may override."""
        return _ZINC22_TANIMOTO[pool_idx]

    def _maybe_inject_hallucination(self, smiles: str, idx: int, seed: str) -> str:
        """Hook for test-only hallucination injection. Default: no-op."""
        return smiles

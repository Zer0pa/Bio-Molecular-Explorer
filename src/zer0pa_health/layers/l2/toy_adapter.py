"""L2 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Same public interface as L2StubAdapter.process() but different reward_modifier formula:
  - Base reward: 0.6 (stub uses 0.5)
  - Different SMILES heuristic: count 'c' (aromatic carbon) chars × 0.5 as a bonus
  - Same schema keys (L2PropertyOutput fields + inchikey)

The output SHAPE is identical; the VALUES differ.
All falsifier classes emitted are identical to L2StubAdapter.

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import re
from typing import Any

from zer0pa_health.contracts.l2 import (
    L2PropertyInput,
    L2PropertyOutput,
)
from zer0pa_health.envelope import (
    Backend,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_invalid_smiles,
    detect_nan_or_nonfinite,
    detect_stub_laundering,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id

# ---------------------------------------------------------------------------
# Module-level SMILES helpers (same as stub but independent copy)
# ---------------------------------------------------------------------------

_BRACKET_RE = re.compile(r"\[.*?\]")
_AROMATIC_RING_RE = re.compile(r"c1ccc")


def _strip_brackets(smiles: str) -> str:
    return _BRACKET_RE.sub("", smiles)


def _count_non_bracket_atoms(smiles: str) -> int:
    stripped = _strip_brackets(smiles)
    count = 0
    i = 0
    while i < len(stripped):
        ch = stripped[i].lower()
        if ch == "c" and i + 1 < len(stripped) and stripped[i + 1].lower() == "l":
            count += 1
            i += 2
        elif ch == "b" and i + 1 < len(stripped) and stripped[i + 1].lower() == "r":
            count += 1
            i += 2
        elif ch in ("b", "c", "n", "o", "p", "s", "f", "i"):
            count += 1
            i += 1
        else:
            i += 1
    return count


def _count_double_bonds(smiles: str) -> int:
    return smiles.count("=")


def _count_aromatic_rings(smiles: str) -> int:
    return len(_AROMATIC_RING_RE.findall(smiles.lower()))


def _count_no_atoms(smiles: str) -> int:
    return smiles.count("N") + smiles.count("O") + smiles.count("n") + smiles.count("o")


def _best_effort_canonical_smiles(smiles: str) -> str:
    s = smiles.strip()
    result: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "[":
            j = s.index("]", i) + 1
            result.append(s[i:j])
            i = j
        else:
            result.append(s[i].upper() if s[i].isalpha() and s[i].lower() in "bcnospfi" else s[i])
            i += 1
    return "".join(result)


def _compute_descriptors(smiles: str) -> dict[str, float]:
    n_atoms = _count_non_bracket_atoms(smiles)
    n_double = _count_double_bonds(smiles)
    mol_weight_proxy = float(n_atoms) * 13.0 + float(n_double) * 14.0
    return {
        "mol_weight_proxy": mol_weight_proxy,
        "atom_count_proxy": float(n_atoms),
        "double_bond_count": float(n_double),
    }


def _compute_admet(smiles: str) -> dict[str, float]:
    n_aromatic = _count_aromatic_rings(smiles)
    n_no = _count_no_atoms(smiles)
    logP_proxy = float(n_aromatic) * 0.7
    tpsa_proxy = float(n_no) * 23.0
    return {
        "logP_proxy": logP_proxy,
        "tpsa_proxy": tpsa_proxy,
        "aromatic_ring_count_proxy": float(n_aromatic),
        "no_atom_count_proxy": float(n_no),
    }


def _compute_liability_flags(
    smiles: str, mol_weight_proxy: float, logP_proxy: float
) -> list[str]:
    flags: list[str] = []
    if mol_weight_proxy > 500.0 or logP_proxy > 5.0:
        flags.append("lipinski_violation")
    if "[N+]" in smiles:
        flags.append("PAINS")
    if "N(" in smiles.upper() and "c1ccc" in smiles.lower():
        flags.append("hERG_liability")
    return flags


def _count_aromatic_c_lower(smiles: str) -> int:
    """Count lowercase 'c' (aromatic carbon) characters in SMILES.

    TOY DIFFERENTIATOR: This is the distinct heuristic vs the stub.
    Stub uses no such bonus; toy adapter uses count('c') × 0.5 as a
    reward bonus (aromatic scaffolds get a mild reward bonus in this toy).
    """
    stripped = _strip_brackets(smiles)
    return stripped.count("c")


def _compute_toy_reward_modifier(
    smiles: str,
    liability_flags: list[str],
    retrosynth_feedback: Any,
) -> float:
    """TOY reward modifier formula.

    Base reward: 0.6 (vs 0.5 in stub)
    Adjustments:
      1. retrosynth_feedback.routes_found is False → subtract 0.4
      2. retrosynth_feedback.route_score → subtract (1 - route_score) × 0.2
      3. Each liability flag → subtract 0.05
      4. Aromatic-c bonus: count('c') × 0.5 added as min(0.1, count*0.01)
         (capped at 0.1 to prevent reward inflation)
    Clamped to [-1.0, 1.0].
    """
    reward = 0.6  # TOY base (different from stub's 0.5)

    if retrosynth_feedback is not None:
        if not retrosynth_feedback.routes_found:
            reward -= 0.4
        reward -= (1.0 - retrosynth_feedback.route_score) * 0.2

    for _ in liability_flags:
        reward -= 0.05

    # TOY DIFFERENTIATOR: small aromatic-c bonus
    n_c = _count_aromatic_c_lower(smiles)
    aromatic_bonus = min(0.1, n_c * 0.5 * 0.01)  # count × 0.5 × scale
    reward += aromatic_bonus

    return max(-1.0, min(1.0, reward))


class L2ToyAdapter:
    """L2 toy adapter — different reward_modifier formula, identical schema.

    Use .process(input, run_id=None, *, mechanism_escalation=False) -> LayerEnvelope
    Same interface as L2StubAdapter.
    """

    NAME = "L2ToyAdapter"
    VERSION = "0.1.0"
    ENGINE = "toy_aromatic_c_heuristic"

    def process(
        self,
        input: L2PropertyInput,
        run_id: str | None = None,
        *,
        mechanism_escalation: bool = False,
    ) -> LayerEnvelope:
        _run_id = run_id or new_run_id()
        smiles = input.molecule.smiles
        falsifier_items = []

        # Step 1: SMILES validity
        smiles_item = detect_invalid_smiles(smiles)
        falsifier_items.append(smiles_item)

        if smiles_item.status == FalsifierStatus.FAIL:
            output = L2PropertyOutput(
                smiles=smiles,
                canonical_smiles=smiles,
                descriptors={},
                admet_scores={},
                liability_flags=[],
                reward_modifier=0.0,
                valid_smiles=False,
            )
            input_payload = input.model_dump()
            output_payload = output.model_dump()
            return LayerEnvelope(
                run_id=_run_id,
                layer=LayerName.L2,
                tool_adapter=ToolAdapter(
                    name=self.NAME,
                    version=self.VERSION,
                    backend=Backend.STUB,
                    engine=self.ENGINE,
                ),
                output=output_payload,
                confidence=EnvelopeConfidence(
                    score=0.0,
                    band=ConfidenceBand.LOW,
                    basis=["invalid_smiles_hard_fail", "toy_aromatic_c_heuristic"],
                ),
                falsifier=EnvelopeFalsifier(
                    status=FalsifierStatus.FAIL,
                    items=falsifier_items,
                ),
                audit=EnvelopeAudit(
                    audit_record_id=audit_id(),
                    input_hash=sha256_of_obj(input_payload),
                    output_hash=sha256_of_obj(output_payload),
                    source_manifest_refs=[],
                ),
                back_edges=[],
            )

        # Step 2: descriptors + ADMET
        canonical = _best_effort_canonical_smiles(smiles)
        descriptors = _compute_descriptors(smiles)
        admet_scores = _compute_admet(smiles)

        mol_weight_proxy = descriptors["mol_weight_proxy"]
        logP_proxy = admet_scores["logP_proxy"]

        # Step 3: liability flags
        liability_flags = _compute_liability_flags(smiles, mol_weight_proxy, logP_proxy)

        # Step 4: TOY reward modifier
        reward_modifier = _compute_toy_reward_modifier(
            smiles, liability_flags, input.retrosynth_feedback
        )

        # Step 5: NaN check
        all_numeric = list(descriptors.values()) + list(admet_scores.values()) + [reward_modifier]
        nan_item = detect_nan_or_nonfinite(all_numeric, context="L2_toy_outputs")
        falsifier_items.append(nan_item)

        if nan_item.status == FalsifierStatus.FAIL:
            output = L2PropertyOutput(
                smiles=smiles,
                canonical_smiles=canonical,
                descriptors=descriptors,
                admet_scores=admet_scores,
                liability_flags=liability_flags,
                reward_modifier=0.0,
                valid_smiles=True,
            )
            input_payload = input.model_dump()
            output_payload = output.model_dump()
            return LayerEnvelope(
                run_id=_run_id,
                layer=LayerName.L2,
                tool_adapter=ToolAdapter(
                    name=self.NAME,
                    version=self.VERSION,
                    backend=Backend.STUB,
                    engine=self.ENGINE,
                ),
                output=output_payload,
                confidence=EnvelopeConfidence(
                    score=0.0,
                    band=ConfidenceBand.LOW,
                    basis=["nonfinite_output_hard_fail", "toy_aromatic_c_heuristic"],
                ),
                falsifier=EnvelopeFalsifier(
                    status=FalsifierStatus.FAIL,
                    items=falsifier_items,
                ),
                audit=EnvelopeAudit(
                    audit_record_id=audit_id(),
                    input_hash=sha256_of_obj(input.model_dump()),
                    output_hash=sha256_of_obj(output_payload),
                    source_manifest_refs=[],
                ),
                back_edges=[],
            )

        # Step 6: stub laundering
        laundering_item = detect_stub_laundering(
            backend="stub",
            claim_kind="mechanism_escalation",
            mechanism_escalation=mechanism_escalation,
        )
        falsifier_items.append(laundering_item)

        # Step 7: clinical overclaim
        output_for_check = L2PropertyOutput(
            smiles=smiles,
            canonical_smiles=canonical,
            descriptors=descriptors,
            admet_scores=admet_scores,
            liability_flags=liability_flags,
            reward_modifier=reward_modifier,
            valid_smiles=True,
        )
        overclaim_item = detect_clinical_overclaim(output_for_check.model_dump_json())
        falsifier_items.append(overclaim_item)

        # Step 8: overall status
        any_fail = any(item.status == FalsifierStatus.FAIL for item in falsifier_items)
        overall_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        # Step 9: envelope
        input_payload = input.model_dump()
        output_payload = output_for_check.model_dump()

        return LayerEnvelope(
            run_id=_run_id,
            layer=LayerName.L2,
            tool_adapter=ToolAdapter(
                name=self.NAME,
                version=self.VERSION,
                backend=Backend.STUB,
                engine=self.ENGINE,
            ),
            output=output_payload,
            confidence=EnvelopeConfidence(
                score=0.48,
                band=ConfidenceBand.MEDIUM,
                basis=[
                    "toy_aromatic_c_heuristic",
                    "string_heuristics_only",
                    f"mol_weight_proxy={mol_weight_proxy:.1f}",
                    f"logP_proxy={logP_proxy:.2f}",
                    f"liability_flags={liability_flags}",
                    f"reward_modifier={reward_modifier:.3f}",
                ],
            ),
            falsifier=EnvelopeFalsifier(
                status=overall_status,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_payload),
                output_hash=sha256_of_obj(output_payload),
                source_manifest_refs=[],
            ),
            back_edges=[],
        )

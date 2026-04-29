"""L2 property / formulation / ADMET stub adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter hierarchy
-----------------
L2StubAdapter       — CPU-side, string-heuristic proxies, backend=stub (default)
L2DeepXDERunpodAdapter — Parked; see parked_runpod.py

STUB-GRADE HEURISTICS — documented explicitly per PRD section 4 / L2 contract:
- All descriptors and ADMET scores are deterministic string-based proxies.
- NO RDKit, DeepChem, or cheminformatics library is used.
- Same SMILES string → identical numbers, always. This is intentional for
  Prefect-style memoization (L6 cache-key behaviour).
- These proxies are NOT predictive chemistry. They exist to verify the
  falsification/audit/back-edge plumbing end-to-end while real chemistry tools
  (RDKit, DeepChem) are swapped in behind the same contract interface.
- Do NOT use any output of this adapter as scientific evidence for drug properties.
"""

from __future__ import annotations

import math
import re
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
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
# Canonical SMILES — best-effort, no RDKit
# ---------------------------------------------------------------------------

def _best_effort_canonical_smiles(smiles: str) -> str:
    """Return a best-effort canonical SMILES without RDKit.

    Approach: strip leading/trailing whitespace; normalise non-bracket atom
    symbols to upper-case (bracket atoms like [nH] are left as-is because
    bracket content has case-sensitive semantics).

    This is explicitly NOT a true canonical form. When RDKit is swapped in,
    this function is replaced by `Chem.MolToSmiles(Chem.MolFromSmiles(s))`.
    The stub is deterministic: same input → same output.
    """
    s = smiles.strip()
    # Non-bracket portions: uppercase single-letter organic subset atoms.
    # Bracket content is preserved verbatim.
    result: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "[":
            # find closing bracket, preserve verbatim
            j = s.index("]", i) + 1
            result.append(s[i:j])
            i = j
        else:
            result.append(s[i].upper() if s[i].isalpha() and s[i].lower() in "bcnospfi" else s[i])
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Stub-grade descriptor computation
# ---------------------------------------------------------------------------

_BRACKET_RE = re.compile(r"\[.*?\]")
_AROMATIC_RING_RE = re.compile(r"c1ccc")  # toy aromatic detection


def _strip_brackets(smiles: str) -> str:
    """Remove bracket atoms from SMILES for non-bracket atom counting."""
    return _BRACKET_RE.sub("", smiles)


def _count_non_bracket_atoms(smiles: str) -> int:
    """Count organic-subset atoms (non-bracket) — B,C,N,O,P,S,F,Cl,Br,I.

    STUB-GRADE: counts letters in the organic subset ignoring aromaticity
    case-sensitivity (both C and c count). This intentionally over-counts
    some molecules and under-counts others; it is only for plumbing tests.
    """
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
    """Count '=' characters in SMILES (proxy for double bonds; stub-grade)."""
    return smiles.count("=")


def _count_aromatic_rings(smiles: str) -> int:
    """Toy aromatic ring count: count non-overlapping occurrences of 'c1ccc'.

    STUB-GRADE heuristic. Real aromaticity detection requires ring perception.
    """
    return len(_AROMATIC_RING_RE.findall(smiles.lower()))


def _count_no_atoms(smiles: str) -> int:
    """Count N and O atoms (both bracket and non-bracket) — proxy for TPSA.

    STUB-GRADE: counts all 'n'/'o'/'N'/'O' characters in the full SMILES
    (including inside brackets). Over-counts decorated atoms but is deterministic.
    """
    return smiles.count("N") + smiles.count("O") + smiles.count("n") + smiles.count("o")


def _compute_descriptors(smiles: str) -> dict[str, float]:
    """Compute deterministic toy molecular descriptors from SMILES string.

    STUB-GRADE — These are string-feature proxies, not real molecular descriptors.
    Formula (documented for audit trail):
      mol_weight_proxy = count(non-bracket atoms) * 13.0 + count('=') * 14.0
        Rationale: 13.0 is ~half the average atomic mass increment per heavy atom
        in drug-like molecules (very rough); 14.0 adds mass for each double bond.
    """
    n_atoms = _count_non_bracket_atoms(smiles)
    n_double = _count_double_bonds(smiles)
    mol_weight_proxy = float(n_atoms) * 13.0 + float(n_double) * 14.0
    return {
        "mol_weight_proxy": mol_weight_proxy,
        "atom_count_proxy": float(n_atoms),
        "double_bond_count": float(n_double),
    }


def _compute_admet(smiles: str) -> dict[str, float]:
    """Compute deterministic toy ADMET scores from SMILES string.

    STUB-GRADE — These are string-feature proxies, not real ADMET predictions.
    Formulas:
      logP_proxy = aromatic_ring_count * 0.7
        Rationale: aromatic rings increase lipophilicity; 0.7 per ring is a
        crude linear proxy. Real logP uses atom contributions (Wildman-Crippen).
      tpsa_proxy = count(N/O atoms) * 23.0
        Rationale: N and O atoms contribute to polar surface area; 23.0 Å²
        per N/O is ~half the average contribution used in simple TPSA methods.
        Real TPSA is bond-type dependent; this stub is purely atom-count based.
    """
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


# ---------------------------------------------------------------------------
# Liability flag detection
# ---------------------------------------------------------------------------

def _compute_liability_flags(
    smiles: str,
    mol_weight_proxy: float,
    logP_proxy: float,
) -> list[str]:
    """Compute stub-grade liability flags from SMILES features.

    Each heuristic is explicitly documented as stub-grade below.

    lipinski_violation:
        Triggered if mol_weight_proxy > 500 OR logP_proxy > 5.
        STUB-GRADE: Real Lipinski Rule of 5 uses: MW > 500, cLogP > 5,
        HBD > 5, HBA > 10. This stub checks only the MW and logP proxies
        since we lack bond-type HBD/HBA counting.

    PAINS:
        Triggered if SMILES contains '[N+]'.
        STUB-GRADE: Real PAINS filtering uses ~480 SMARTS substructure patterns
        (Baell & Holloway 2010). This toy heuristic catches only one class of
        reactive/promiscuous fragments (charged nitrogen). Document as
        incomplete.

    hERG_liability:
        Triggered if SMILES contains a basic amine proxy ('N(') AND an
        aromatic ring proxy ('c1ccc').
        STUB-GRADE: Real hERG liability prediction uses pharmacophore or ML
        models (Chemprop, etc.). The key pharmacophoric feature of hERG blockers
        is a basic nitrogen 3.6 Å from a hydrophobic aromatic group. This
        string-level heuristic is a gross over-approximation; it will produce
        many false positives. It exists only to exercise the liability-flag
        back-edge plumbing.
    """
    flags: list[str] = []

    # Lipinski-proxy violation
    if mol_weight_proxy > 500.0 or logP_proxy > 5.0:
        flags.append("lipinski_violation")

    # PAINS proxy (charged nitrogen)
    if "[N+]" in smiles:
        flags.append("PAINS")

    # hERG liability proxy: basic amine + aromatic ring
    if "N(" in smiles.upper() and "c1ccc" in smiles.lower():
        flags.append("hERG_liability")

    return flags


# ---------------------------------------------------------------------------
# Reward modifier computation (Inversion A: back-edges before forward passes)
# ---------------------------------------------------------------------------

def _compute_reward_modifier(
    liability_flags: list[str],
    retrosynth_feedback: Any,
) -> float:
    """Compute REINVENT-style reward modifier including L2.5 back-edge.

    Base reward: 0.5
    Adjustments (in order):
      1. retrosynth_feedback.routes_found is False → subtract 0.4
         (Inversion A: synthesis infeasibility feeds back to L2 scoring
          before any forward promotion; per PRD section 4, claim 7)
      2. retrosynth_feedback.route_score provided → subtract (1 - route_score) * 0.2
         (penalise low-quality routes proportionally)
      3. Each liability flag → subtract 0.05
         (stack penalty per flag)
    Final value clamped to [-1.0, 1.0].
    """
    reward = 0.5

    if retrosynth_feedback is not None:
        if not retrosynth_feedback.routes_found:
            reward -= 0.4
        # route_score is always present (Field ge=0, le=1 with default in contract)
        reward -= (1.0 - retrosynth_feedback.route_score) * 0.2

    for _ in liability_flags:
        reward -= 0.05

    # Clamp
    reward = max(-1.0, min(1.0, reward))
    return reward


# ---------------------------------------------------------------------------
# score_property — public functional entry-point
# ---------------------------------------------------------------------------

def score_property(smiles: str) -> dict[str, float]:
    """Return merged descriptor + ADMET dict for a given SMILES.

    Deterministic; same SMILES → same dict. No side effects.
    Exported from the package for downstream consumers that want raw scores
    without building a full LayerEnvelope.
    """
    desc = _compute_descriptors(smiles)
    admet = _compute_admet(smiles)
    return {**desc, **admet}


# ---------------------------------------------------------------------------
# L2StubAdapter
# ---------------------------------------------------------------------------

class L2StubAdapter:
    """L2 property / formulation / ADMET stub adapter.

    Implements the L2 contract (contracts/l2.py) using deterministic string-
    heuristic proxies. No RDKit or cheminformatics runtime dependency.

    Swap path to production:
        Replace this adapter with an RDKit/DeepChem adapter that accepts the
        same L2PropertyInput and returns a LayerEnvelope with the same shape.
        The envelope contract is frozen; only the compute inside changes.
    """

    NAME = "L2StubAdapter"
    VERSION = "0.1.0"
    ENGINE = "string_heuristics_stub"

    def process(
        self,
        input: L2PropertyInput,
        run_id: str | None = None,
        *,
        mechanism_escalation: bool = False,
    ) -> LayerEnvelope:
        """Process a single molecule through the L2 property/formulation gate.

        Parameters
        ----------
        input:
            L2PropertyInput (see contracts/l2.py).
        run_id:
            Caller-supplied run ID (e.g. from Prefect). If None, a new one is
            generated.
        mechanism_escalation:
            If True, triggers STUB_LAUNDERING falsifier FAIL. This flag is set
            by L6 when it attempts to escalate stub outputs to mechanism claims,
            which is forbidden (PRD section 3).

        Returns
        -------
        LayerEnvelope
            Always returns an envelope; failures are encoded in
            envelope.falsifier.status rather than raised as exceptions.
        """
        _run_id = run_id or new_run_id()
        smiles = input.molecule.smiles
        falsifier_items = []

        # ------------------------------------------------------------------
        # Step 1: SMILES validity check
        # ------------------------------------------------------------------
        smiles_item = detect_invalid_smiles(smiles)
        falsifier_items.append(smiles_item)

        if smiles_item.status == FalsifierStatus.FAIL:
            # Hard fail: do not compute scores
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
                    basis=["invalid_smiles_hard_fail", "stub_descriptor_proxies"],
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

        # ------------------------------------------------------------------
        # Step 2: Compute deterministic descriptors and ADMET
        # ------------------------------------------------------------------
        canonical = _best_effort_canonical_smiles(smiles)
        descriptors = _compute_descriptors(smiles)
        admet_scores = _compute_admet(smiles)

        mol_weight_proxy = descriptors["mol_weight_proxy"]
        logP_proxy = admet_scores["logP_proxy"]

        # ------------------------------------------------------------------
        # Step 3: Liability flags
        # ------------------------------------------------------------------
        liability_flags = _compute_liability_flags(smiles, mol_weight_proxy, logP_proxy)

        # ------------------------------------------------------------------
        # Step 4: Reward modifier (Inversion A — L2.5 back-edge applied here)
        # ------------------------------------------------------------------
        reward_modifier = _compute_reward_modifier(
            liability_flags, input.retrosynth_feedback
        )

        # ------------------------------------------------------------------
        # Step 5: NaN / nonfinite check over all numeric outputs
        # ------------------------------------------------------------------
        all_numeric = list(descriptors.values()) + list(admet_scores.values()) + [reward_modifier]
        nan_item = detect_nan_or_nonfinite(all_numeric, context="L2_outputs")
        falsifier_items.append(nan_item)

        if nan_item.status == FalsifierStatus.FAIL:
            output = L2PropertyOutput(
                smiles=smiles,
                canonical_smiles=canonical,
                descriptors=descriptors,
                admet_scores=admet_scores,
                liability_flags=liability_flags,
                reward_modifier=0.0,  # zero out on NaN fail
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
                    basis=["nonfinite_output_hard_fail", "stub_descriptor_proxies"],
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

        # ------------------------------------------------------------------
        # Step 6: Stub laundering check
        # ------------------------------------------------------------------
        laundering_item = detect_stub_laundering(
            backend="stub",
            claim_kind="mechanism_escalation",
            mechanism_escalation=mechanism_escalation,
        )
        falsifier_items.append(laundering_item)

        # ------------------------------------------------------------------
        # Step 7: Clinical overclaim check (paranoid double-check on output)
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # Step 8: Determine overall falsifier status
        # ------------------------------------------------------------------
        any_fail = any(
            item.status == FalsifierStatus.FAIL for item in falsifier_items
        )
        overall_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        # ------------------------------------------------------------------
        # Step 9: Build envelope
        # ------------------------------------------------------------------
        input_payload = input.model_dump()
        output_payload = output_for_check.model_dump()

        confidence_score = 0.5  # stub confidence midpoint in 0.4-0.6 band
        confidence_band = ConfidenceBand.MEDIUM

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
                score=confidence_score,
                band=confidence_band,
                basis=[
                    "stub_descriptor_proxies",
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

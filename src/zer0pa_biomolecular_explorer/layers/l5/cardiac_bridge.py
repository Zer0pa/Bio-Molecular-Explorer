"""L5 cardiac exposure-channel bridge.

Maps unbound plasma Cmax (µM) to fractional channel block for each of the
four CiPA-relevant ion currents: IKr, IKs, INaL, ICaL.

Sign convention for multi_current_balance_score
------------------------------------------------
multi_current_balance_score = (outward_block) - (inward_block)

where:
    outward_block = mean fractional block of IKr + IKs
    inward_block  = mean fractional block of INaL + ICaL

INTERPRETATION (research-only indicator; NOT a clinical safety claim):
  - HIGHER score → more outward currents blocked relative to inward currents
    → less repolarisation reserve → greater APD-prolongation tendency in
    research-only QSP/CiPA-style multi-current models.
  - LOWER (more negative) score → more inward current block relative to outward
    → APD-prolongation tendency reduced in the same research models.

  This is an INDICATOR for downstream researcher inspection, not a verdict.
  No clinical, diagnostic, prescribing, or safety claim is implied or supported
  by this score in any direction.

Canonical examples:
  - Dofetilide: blocks only IKr (outward), score ≈ +IKr_block > 0 (high risk indicator).
  - Verapamil:  blocks IKr (outward) AND ICaL (inward); ICaL block offsets IKr block,
                so score is LOWER than dofetilide despite hERG activity.
  - Ranolazine: blocks IKr (outward) and INaL (inward); INaL block reduces score
                relative to a pure outward blocker.

Current-to-gene mapping
-----------------------
  KCNH2_hERG_IKr           → "IKr"   (outward; main repolarising current)
  SCN5A_Nav1_5_INa_INaL    → "INaL"  (inward; late sodium; dominant late-Na target;
                                       NOTE: we map SCN5A to INaL because late-INa is
                                       the pharmacologically relevant target for CiPA
                                       compounds in this research context. Peak INa is
                                       not captured by canned IC50 values in current
                                       fixtures. Document as stub assumption.)
  KCNQ1_Kv7_1_IKs          → "IKs"   (outward; slow delayed rectifier)
  CACNA1C_CaV1_2_ICaL      → "ICaL"  (inward; L-type calcium)

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.contracts.l5 import L5ChannelExposureBridge

# Gene panel keys to current name and direction (outward=True, inward=False)
_GENE_TO_CURRENT: dict[str, tuple[str, bool]] = {
    "KCNH2_hERG_IKr": ("IKr", True),       # outward
    "SCN5A_Nav1_5_INa_INaL": ("INaL", False),  # inward (late Na — dominant target)
    "KCNQ1_Kv7_1_IKs": ("IKs", True),      # outward
    "CACNA1C_CaV1_2_ICaL": ("ICaL", False),  # inward
}

# Canonical 4 genes required by CiPA multi-current framework
CANONICAL_GENES = list(_GENE_TO_CURRENT.keys())


def _hill1(cmax_uM: float, ic50_uM: float) -> float:
    """Hill equation, n=1: fractional_block = C / (IC50 + C)."""
    if ic50_uM <= 0.0:
        return 1.0
    if cmax_uM <= 0.0:
        return 0.0
    return cmax_uM / (ic50_uM + cmax_uM)


def cardiac_bridge(
    cmax_unbound_uM: float,
    channel_panel_canned: dict,
) -> L5ChannelExposureBridge:
    """Compute fractional channel block and multi-current balance score.

    Parameters
    ----------
    cmax_unbound_uM:
        Unbound peak plasma concentration in micromolar (from L5 PK model).
    channel_panel_canned:
        Dict keyed by canonical gene strings (e.g. "KCNH2_hERG_IKr") with at
        minimum an "ic50_uM" field (float or None).

    Returns
    -------
    L5ChannelExposureBridge with:
        fractional_block_at_cmax: dict[current_name, fraction (0-1)]
        multi_current_balance_score: float in [-1, 1]; sign convention above.

    Channels with ic50_uM = None are set to fractional_block = 0.0 and recorded
    in the explicit_absence field (returned as a standalone list). The caller
    should use explicit_absence to build back_edges to L1.
    """
    fractional_block: dict[str, float] = {}
    explicit_absence: list[str] = []

    for gene_key, (current_name, _is_outward) in _GENE_TO_CURRENT.items():
        entry = channel_panel_canned.get(gene_key)
        if entry is None:
            # Gene not present in panel at all
            fractional_block[current_name] = 0.0
            explicit_absence.append(gene_key)
            continue

        ic50 = entry.get("ic50_uM")
        if ic50 is None:
            # Explicit absence recorded in fixture
            fractional_block[current_name] = 0.0
            explicit_absence.append(gene_key)
        else:
            fractional_block[current_name] = _hill1(cmax_unbound_uM, float(ic50))

    # Compute multi_current_balance_score
    # outward: IKr, IKs; inward: INaL, ICaL
    outward_block = (
        fractional_block.get("IKr", 0.0) + fractional_block.get("IKs", 0.0)
    )
    inward_block = (
        fractional_block.get("INaL", 0.0) + fractional_block.get("ICaL", 0.0)
    )

    # Normalise to [-1, 1] by dividing by max possible (both outward = 1.0)
    # Max outward = 2.0 (IKr=1 + IKs=1); max inward = 2.0
    # Use simple difference clamped to [-1, 1] — each term is in [0,1] so
    # difference is in [-2, 2]; divide by 2 to map to [-1, 1].
    raw_score = (outward_block - inward_block) / 2.0
    score = max(-1.0, min(1.0, raw_score))

    bridge = L5ChannelExposureBridge(
        cmax_unbound_uM=cmax_unbound_uM,
        fractional_block_at_cmax=fractional_block,
        multi_current_balance_score=score,
    )
    # Attach explicit_absence as a free attribute via __dict__ so callers can
    # retrieve it without modifying the Pydantic contract schema.
    bridge.__dict__["_explicit_absence"] = explicit_absence
    return bridge


def get_explicit_absence(bridge: L5ChannelExposureBridge) -> list[str]:
    """Retrieve the explicit_absence list attached to a cardiac bridge result."""
    return bridge.__dict__.get("_explicit_absence", [])

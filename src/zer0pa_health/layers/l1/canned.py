"""Canned (fixture-backed) outputs for the L1 stub adapter.

Loads compound fixture JSONs and derives realistic-shape stub values.
No RDKit required. No network calls. Deterministic given inchikey + gene.

Real ligand standardization and physics-based simulation will be provided
by the Runpod GPU adapter (OpenFERunpodAdapter).

NOTE: All values are stub canned outputs. Confidence band is MEDIUM (0.4-0.6).
Every output carries basis=["stub_canned_output"] so downstream auditors can
detect that real simulation has NOT been performed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "compounds"

# Map inchikey -> loaded JSON fixture
_COMPOUND_CACHE: dict[str, dict] = {}

_KNOWN_FIXTURES = {
    "IXTMWRCNAAVVAI-UHFFFAOYSA-N": "dofetilide.json",
    "SGTNSNPWRIOYBX-UHFFFAOYSA-N": "verapamil.json",
    "XKLMZUWKNUAPSZ-UHFFFAOYSA-N": "ranolazine.json",
}


def _load_fixture(inchikey: str) -> dict:
    if inchikey in _COMPOUND_CACHE:
        return _COMPOUND_CACHE[inchikey]
    filename = _KNOWN_FIXTURES.get(inchikey)
    if filename is None:
        raise KeyError(f"No canned fixture for inchikey={inchikey!r}")
    path = _FIXTURES_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    _COMPOUND_CACHE[inchikey] = data
    return data


def _gene_key_prefix(gene: str) -> str:
    """Map canonical gene name to fixture key prefix."""
    _MAP = {
        "KCNH2": "KCNH2_hERG_IKr",
        "SCN5A": "SCN5A_Nav1_5_INa_INaL",
        "KCNQ1": "KCNQ1_Kv7_1_IKs",
        "CACNA1C": "CACNA1C_CaV1_2_ICaL",
    }
    return _MAP.get(gene, gene)


def _seed_float(inchikey: str, gene: str, salt: str, lo: float, hi: float) -> float:
    """Deterministic pseudo-random float in [lo, hi] from inchikey+gene+salt."""
    h = hashlib.sha256(f"{inchikey}|{gene}|{salt}".encode()).hexdigest()
    frac = int(h[:8], 16) / 0xFFFFFFFF
    return lo + frac * (hi - lo)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_REQUIRED_PANEL_GENES = ("KCNH2", "SCN5A", "KCNQ1", "CACNA1C")


def canned_channel_panel(inchikey: str) -> dict:
    """Return the channel_panel_canned blob from the compound fixture.

    Raises KeyError if no fixture exists for inchikey.

    The returned dict is a copy of the fixture's channel_panel_canned blob.
    Callers should verify all four canonical genes are present (KCNH2, SCN5A,
    KCNQ1, CACNA1C) — the fixture format uses gene-prefixed keys.
    """
    fixture = _load_fixture(inchikey)
    panel = fixture["channel_panel_canned"]
    # Build a normalised gene->data dict keyed by canonical gene name
    normalised: dict[str, dict] = {}
    for raw_key, entry in panel.items():
        # raw_key is like "KCNH2_hERG_IKr" — use the part before first underscore
        gene = raw_key.split("_")[0]
        normalised[gene] = dict(entry)
    return normalised


def canned_pose(inchikey: str, gene: str) -> list[dict]:
    """Return 3 stub docking poses for (inchikey, gene).

    Each pose has:
      - pose_index: 0, 1, 2
      - confidence: 0.4-0.7 band (deterministic from inchikey+gene)
      - estimated_binding_kcal_mol: -8 to -5 kcal/mol band
      - structure_basis: "stub"

    Basis is NOT a real physics result. Confidence is medium only.
    """
    poses = []
    for i in range(3):
        conf = _seed_float(inchikey, gene, f"pose_conf_{i}", 0.40, 0.70)
        score = _seed_float(inchikey, gene, f"pose_score_{i}", -8.0, -5.0)
        poses.append(
            {
                "pose_index": i,
                "confidence": round(conf, 3),
                "estimated_binding_kcal_mol": round(score, 3),
                "structure_basis": "stub",
            }
        )
    return poses


def canned_binding(inchikey: str, gene: str) -> dict:
    """Return stub binding estimate for (inchikey, gene).

    Returns:
        delta_g_kcal_mol: float in [-10, -4] range
        uncertainty_kcal_mol: float in [0.5, 2.0] range
        basis: ["stub_canned_output"]
        confidence: 0.4-0.6 medium band
    """
    dg = _seed_float(inchikey, gene, "binding_dg", -10.0, -4.0)
    unc = _seed_float(inchikey, gene, "binding_unc", 0.5, 2.0)
    conf = _seed_float(inchikey, gene, "binding_conf", 0.40, 0.60)
    return {
        "delta_g_kcal_mol": round(dg, 3),
        "uncertainty_kcal_mol": round(unc, 3),
        "basis": ["stub_canned_output"],
        "confidence": round(conf, 3),
    }


def canned_md(inchikey: str, gene: str) -> dict:
    """Return stub MD simulation result for (inchikey, gene).

    Returns:
        rmsd_nm: float (typical 0.1-0.4 nm range for ligand in binding pocket)
        convergence_metric: float 0-1 (medium-band, 0.4-0.7)
        n_frames: int (stub = 100)
        basis: ["stub_canned_output"]
    """
    rmsd = _seed_float(inchikey, gene, "md_rmsd", 0.10, 0.40)
    conv = _seed_float(inchikey, gene, "md_conv", 0.40, 0.70)
    return {
        "rmsd_nm": round(rmsd, 4),
        "convergence_metric": round(conv, 4),
        "n_frames": 100,
        "basis": ["stub_canned_output"],
    }


def canned_fep(inchikey_a: str, inchikey_b: str, gene: str) -> dict:
    """Return stub FEP result for perturbation A->B on (gene).

    Returns:
        ddg_kcal_mol: float [-3, 3] range
        uncertainty_kcal_mol: float [0.3, 1.5]
        convergence_ok: bool (always True for stub)
        basis: ["stub_canned_output"]
    """
    ddg = _seed_float(inchikey_a + inchikey_b, gene, "fep_ddg", -3.0, 3.0)
    unc = _seed_float(inchikey_a + inchikey_b, gene, "fep_unc", 0.3, 1.5)
    return {
        "ddg_kcal_mol": round(ddg, 3),
        "uncertainty_kcal_mol": round(unc, 3),
        "convergence_ok": True,
        "basis": ["stub_canned_output"],
    }

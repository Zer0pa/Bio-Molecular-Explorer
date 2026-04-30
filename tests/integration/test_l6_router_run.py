"""L6 router-driven cardiac wedge run tests.

Demonstrates that the cardiac wedge can be walked by the L6 state graph
(not just direct adapter calls), recording per-transition decisions in
the audit log.
"""

from __future__ import annotations

import json
from pathlib import Path

from zer0pa_health.runs import run_cardiac_via_l6_router


_DOFETILIDE_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"
_DOFETILIDE_INCHIKEY = "IXTMWRCNAAVVAI-UHFFFAOYSA-N"


def test_l6_router_walks_full_cardiac_chain(tmp_path):
    res = run_cardiac_via_l6_router(
        compound="dofetilide",
        runtime_root=tmp_path,
        smiles=_DOFETILIDE_SMILES,
        inchikey=_DOFETILIDE_INCHIKEY,
        cmax_unbound_uM=0.001,
    )
    # 6 layers in the chain → 6 transitions
    layers_visited = [t["layer"] for t in res.transitions]
    assert layers_visited == ["L1", "L2.5", "L2", "L3", "L4", "L5"]
    # No blocks expected on the seed compound + healthy sensor
    assert res.block_count == 0


def test_l6_router_records_decisions_to_audit(tmp_path):
    res = run_cardiac_via_l6_router(
        compound="dofetilide",
        runtime_root=tmp_path,
        smiles=_DOFETILIDE_SMILES,
        inchikey=_DOFETILIDE_INCHIKEY,
    )
    # Per-transition decisions written to audit/decisions.jsonl
    decisions_path = tmp_path / "audit" / "runs" / res.run_id / "decisions.jsonl"
    assert decisions_path.exists()
    lines = [line for line in decisions_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 6  # one per layer transition
    for line in lines:
        rec = json.loads(line)
        assert rec["actor"] == "l6_router"
        assert rec["decision_kind"] in {
            "promote",
            "downgrade",
            "reroute",
            "block",
            "backedge",
            "hold",
            "exec",
        }


def test_l6_router_promotes_on_clean_run(tmp_path):
    res = run_cardiac_via_l6_router(
        compound="ranolazine",
        runtime_root=tmp_path,
        smiles="COc1ccccc1OCC(O)CN1CCN(CC(=O)Nc2c(C)cccc2C)CC1",
        inchikey="XKLMZUWKNUAPSZ-UHFFFAOYSA-N",
    )
    # We expect at least 1 promote on a clean dofetilide-ish run
    assert res.promote_count >= 1
    # Audit-validate the run
    from zer0pa_health.audit import AuditValidator

    counts = AuditValidator(tmp_path / "audit", res.run_id).validate()
    assert counts["runs"] == 1
    assert counts["decisions"] == 6

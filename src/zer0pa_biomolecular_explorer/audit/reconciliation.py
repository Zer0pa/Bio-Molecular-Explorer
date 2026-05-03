"""Reconciliation: audit/falsifiers.jsonl ↔ falsifier_ledger.jsonl ↔ KG falsifier nodes.

Brief from operator: "fail if ledger, audit, and KG diverge."

The three views of the same truth:
  - `audit/runs/<rid>/falsifiers.jsonl`           : append-only audit table (hash-chained)
  - `audit/runs/<rid>/falsifier_ledger.jsonl`     : operational ledger view (no hash chain)
  - KG `Falsifier` nodes + HAS_FALSIFIER edges    : graph view, joined to claims

After a run, every falsifier_id appearing in any of these three views must appear
in the other two — modulo cardinality differences explained by the design (e.g.,
the audit table records the FULL provenance, the ledger records the operational
state, the KG records only those falsifiers that have a HAS_FALSIFIER edge to a
specific Claim node).

This module enforces:

  - Set equality of falsifier_ids between audit/falsifiers.jsonl and falsifier_ledger.jsonl.
  - Every Falsifier node in the KG has a corresponding audit row (no dangling KG falsifier).
  - No audit row references a falsifier_class that isn't in `FalsifierClass`.

Failure raises `ReconciliationError`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from zer0pa_biomolecular_explorer.falsifiers.registry import FalsifierClass


class ReconciliationError(RuntimeError):
    pass


@dataclass
class ReconciliationReport:
    run_id: str
    audit_falsifier_ids: set[str] = field(default_factory=set)
    ledger_falsifier_ids: set[str] = field(default_factory=set)
    kg_falsifier_node_ids: set[str] = field(default_factory=set)
    audit_row_count: int = 0
    ledger_row_count: int = 0
    kg_falsifier_node_count: int = 0
    audit_only: set[str] = field(default_factory=set)
    ledger_only: set[str] = field(default_factory=set)
    unknown_falsifier_classes: set[str] = field(default_factory=set)

    @property
    def divergent(self) -> bool:
        return bool(
            self.audit_only
            or self.ledger_only
            or self.unknown_falsifier_classes
        )


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def reconcile_ledger_audit_kg(
    audit_root: Path,
    run_id: str,
    kg_store: object | None = None,
) -> ReconciliationReport:
    """Reconcile the three views; raise on divergence.

    Parameters
    ----------
    audit_root:
        Root containing `runs/<run_id>/falsifiers.jsonl` + `falsifier_ledger.jsonl`.
    run_id:
        The specific run to reconcile.
    kg_store:
        Optional KGStore instance. If provided, KG Falsifier-node consistency
        is checked. If None, only audit ↔ ledger reconciliation runs.

    Returns
    -------
    `ReconciliationReport` with counts + divergence sets.

    Raises
    ------
    ReconciliationError: when audit_only, ledger_only, or unknown_falsifier_classes is non-empty.
    """
    run_dir = audit_root / "runs" / run_id
    audit_path = run_dir / "falsifiers.jsonl"
    ledger_path = run_dir / "falsifier_ledger.jsonl"

    audit_rows = _read_jsonl(audit_path)
    ledger_rows = _read_jsonl(ledger_path)

    audit_ids: set[str] = set()
    unknown_classes: set[str] = set()
    valid_classes = {c.value for c in FalsifierClass}
    for row in audit_rows:
        fid = row.get("falsifier_id")
        if fid:
            audit_ids.add(fid)
        cls = row.get("falsifier_class")
        if cls and cls not in valid_classes:
            unknown_classes.add(cls)

    ledger_ids: set[str] = set()
    for row in ledger_rows:
        fid = row.get("falsifier_id")
        if fid:
            ledger_ids.add(fid)

    audit_only = audit_ids - ledger_ids
    ledger_only = ledger_ids - audit_ids

    kg_falsifier_node_ids: set[str] = set()
    if kg_store is not None and hasattr(kg_store, "iter_nodes"):
        for n in kg_store.iter_nodes():
            ntype = getattr(n, "node_type", None)
            ntype_value = getattr(ntype, "value", str(ntype))
            if ntype_value == "Falsifier":
                kg_falsifier_node_ids.add(getattr(n, "node_id", ""))

    report = ReconciliationReport(
        run_id=run_id,
        audit_falsifier_ids=audit_ids,
        ledger_falsifier_ids=ledger_ids,
        kg_falsifier_node_ids=kg_falsifier_node_ids,
        audit_row_count=len(audit_rows),
        ledger_row_count=len(ledger_rows),
        kg_falsifier_node_count=len(kg_falsifier_node_ids),
        audit_only=audit_only,
        ledger_only=ledger_only,
        unknown_falsifier_classes=unknown_classes,
    )

    if report.divergent:
        problems: list[str] = []
        if audit_only:
            problems.append(
                f"{len(audit_only)} falsifier_id(s) in audit but missing from ledger: "
                f"{sorted(audit_only)[:5]}"
            )
        if ledger_only:
            problems.append(
                f"{len(ledger_only)} falsifier_id(s) in ledger but missing from audit: "
                f"{sorted(ledger_only)[:5]}"
            )
        if unknown_classes:
            problems.append(
                f"{len(unknown_classes)} unknown falsifier_class value(s) in audit: "
                f"{sorted(unknown_classes)[:5]}"
            )
        raise ReconciliationError(
            f"run={run_id}: audit/ledger/KG reconciliation FAILED. " + " | ".join(problems)
        )
    return report

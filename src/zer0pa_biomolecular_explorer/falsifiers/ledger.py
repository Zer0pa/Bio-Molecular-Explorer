"""Per-run falsifier ledger — JSONL on disk, append-only.

The ledger lives at `audit/runs/<run_id>/falsifier_ledger.jsonl`. Every
falsifier emission writes one line. The audit/falsifiers.jsonl table mirrors
the same data via `AuditWriter` for hash-chain integrity; the ledger here is
the operational view (read-heavy, no hash chain so cheap to scan).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from zer0pa_biomolecular_explorer.envelope import EnvelopeFalsifierItem, FalsifierStatus
from zer0pa_biomolecular_explorer.falsifiers.registry import FalsifierClass, get_definition
from zer0pa_biomolecular_explorer.ids import utc_now_iso


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    falsifier_id: str
    falsifier_class: FalsifierClass
    layer: str
    run_id: str
    created_at_utc: str
    trigger_condition: str
    status: FalsifierStatus
    evidence: list[str] = Field(default_factory=list)
    backedge_target: str | None = None
    severity: str
    extra: dict[str, str] = Field(default_factory=dict)


class FalsifierLedger:
    def __init__(self, ledger_path: Path) -> None:
        self.path = ledger_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        run_id: str,
        falsifier_class: FalsifierClass,
        layer: str,
        status: FalsifierStatus,
        evidence: list[str] | None = None,
        extra: dict[str, str] | None = None,
        *,
        falsifier_id: str | None = None,
    ) -> EnvelopeFalsifierItem:
        """Emit a falsifier entry to the operational ledger.

        Parameters
        ----------
        falsifier_id:
            Optional pre-existing falsifier_id (e.g., from an envelope's
            EnvelopeFalsifierItem). When provided, the ledger reuses this id —
            critical for ledger ↔ audit reconciliation. When None, a fresh id
            is generated.
        """
        defn = get_definition(falsifier_class)
        from zer0pa_biomolecular_explorer.ids import falsifier_id as _generate_falsifier_id

        fid = falsifier_id if falsifier_id is not None else _generate_falsifier_id(falsifier_class.value)
        entry = LedgerEntry(
            falsifier_id=fid,
            falsifier_class=falsifier_class,
            layer=layer,
            run_id=run_id,
            created_at_utc=utc_now_iso(),
            trigger_condition=defn.trigger_condition,
            status=status,
            evidence=evidence or [],
            backedge_target=defn.backedge_target,
            severity=defn.severity,
            extra=extra or {},
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json() + "\n")

        return EnvelopeFalsifierItem(
            falsifier_id=entry.falsifier_id,
            falsifier_class=falsifier_class.value,
            trigger_condition=entry.trigger_condition,
            status=status,
            evidence=entry.evidence,
        )

    def iter_entries(self) -> Iterable[LedgerEntry]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield LedgerEntry.model_validate_json(line)

    def fail_count_by_class(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.iter_entries():
            if e.status == FalsifierStatus.FAIL:
                counts[e.falsifier_class.value] = counts.get(e.falsifier_class.value, 0) + 1
        return counts

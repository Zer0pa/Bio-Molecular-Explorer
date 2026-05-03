"""Append-only JSONL writer with hash chain.

One JSONL file per audit table. Each append computes:
  record_hash = sha256(prev_record_hash || canonical_json(payload_excluding_hashes))

The chain is per-table-per-run. The genesis prev_record_hash is GENESIS_HASH.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

from zer0pa_biomolecular_explorer.hashing import GENESIS_HASH, canonical_json, hash_chain_link
from zer0pa_biomolecular_explorer.ids import utc_now_iso


class AuditTable(str, Enum):
    RUNS = "runs"
    MOLECULES = "molecules"
    MODEL_TOOLS = "model_tools"
    SOURCE_MANIFEST = "source_manifest"
    PARAMETERS = "parameters"
    CONFIDENCE = "confidence"
    FALSIFIERS = "falsifiers"
    DECISIONS = "decisions"
    ARTIFACTS = "artifacts"
    REPLAY_COMMANDS = "replay_commands"
    OFFLOAD_MANIFEST = "offload_manifest"
    MIDD_ASSESSMENTS = "midd_assessments"


AUDIT_TABLE_FILES: dict[AuditTable, str] = {t: f"{t.value}.jsonl" for t in AuditTable}


class AuditWriter:
    """Append-only JSONL writer rooted at `run_dir / 'audit'`.

    Per-run audit dirs (`audit/runs/<run_id>/`) are recommended; the top-level
    `audit/` dir holds aggregate seed/manifest files.
    """

    def __init__(self, audit_root: Path, run_id: str) -> None:
        self.run_id = run_id
        self.run_dir = audit_root / "runs" / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._tail: dict[AuditTable, str] = {}

    def _path(self, table: AuditTable) -> Path:
        return self.run_dir / AUDIT_TABLE_FILES[table]

    def _read_tail(self, table: AuditTable) -> str:
        if table in self._tail:
            return self._tail[table]
        path = self._path(table)
        if not path.exists() or path.stat().st_size == 0:
            self._tail[table] = GENESIS_HASH
            return GENESIS_HASH
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size == 0:
                self._tail[table] = GENESIS_HASH
                return GENESIS_HASH
            chunk = min(8192, size)
            fh.seek(-chunk, os.SEEK_END)
            data = fh.read().decode("utf-8")
        last_line = data.strip().splitlines()[-1]
        last = json.loads(last_line)
        self._tail[table] = last["record_hash"]
        return self._tail[table]

    def append(self, table: AuditTable, payload: dict[str, Any]) -> dict[str, Any]:
        """Append a record. Stamps created_at_utc/prev_record_hash/record_hash if absent.

        Returns the fully-formed record dict (including all hash-chain fields).
        Caller must NOT pre-compute record_hash; this function is the only legitimate writer.
        """
        if "table" not in payload:
            payload["table"] = table.value
        if payload["table"] != table.value:
            raise ValueError(f"payload['table']={payload['table']!r} does not match {table.value!r}")
        if "created_at_utc" not in payload:
            payload["created_at_utc"] = utc_now_iso()
        if "schema_version" not in payload:
            payload["schema_version"] = "v1"
        if "research_boundary" not in payload:
            from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
            payload["research_boundary"] = RESEARCH_BOUNDARY

        # Hash payload over its semantic content (exclude record_hash itself)
        prev = self._read_tail(table)
        payload_for_hash = {k: v for k, v in payload.items() if k != "record_hash"}
        payload_for_hash["prev_record_hash"] = prev
        record_hash = hash_chain_link(prev, payload_for_hash)
        payload["prev_record_hash"] = prev
        payload["record_hash"] = record_hash

        path = self._path(table)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(payload) + "\n")
        self._tail[table] = record_hash
        return payload

    def list_tables(self) -> list[Path]:
        return sorted([self._path(t) for t in AuditTable if self._path(t).exists()])

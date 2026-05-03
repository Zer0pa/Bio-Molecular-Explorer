"""Audit log validator.

Fails on:
  - missing or non-canonical research_boundary
  - malformed hash chain (broken prev/record link)
  - dangling refs (run_id not present in runs.jsonl)
  - missing required fields
  - PHI / secrets markers
  - unsupported bulk local file references
  - clinical/regulatory-conclusion phrases (the boundary trip)
"""

from __future__ import annotations

import json
from pathlib import Path

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY, boundary_violations
from zer0pa_biomolecular_explorer.hashing import GENESIS_HASH, canonical_json, hash_chain_link
from zer0pa_biomolecular_explorer.audit.writer import AUDIT_TABLE_FILES, AuditTable


class AuditValidationError(RuntimeError):
    pass


_BULK_LOCAL_PATTERNS = (
    "/raw/",
    "/bulk/",
    ".parquet",
    ".hdf5",
    ".h5",
    "data/raw/",
    "data/bulk/",
)

_PHI_MARKERS = ("ssn", "dob:", "patient_name", "mrn:", "date_of_birth")
_SECRET_MARKERS = ("api_key=", "bearer ", "aws_secret", "private_key", "password=")


class AuditValidator:
    def __init__(self, audit_root: Path, run_id: str) -> None:
        self.audit_root = audit_root
        self.run_id = run_id
        self.run_dir = audit_root / "runs" / run_id

    def validate(self) -> dict[str, int]:
        if not self.run_dir.exists():
            raise AuditValidationError(f"run dir does not exist: {self.run_dir}")
        per_table_counts: dict[str, int] = {}
        run_ids_seen: set[str] = set()
        ref_run_ids: set[str] = set()

        for table in AuditTable:
            path = self.run_dir / AUDIT_TABLE_FILES[table]
            count = 0
            if not path.exists():
                per_table_counts[table.value] = 0
                continue

            prev = GENESIS_HASH
            with path.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self._check_record_shape(table, rec, path, lineno)

                    # hash chain
                    if rec["prev_record_hash"] != prev:
                        raise AuditValidationError(
                            f"{path}:{lineno} prev_record_hash mismatch: "
                            f"expected {prev}, got {rec['prev_record_hash']}"
                        )
                    payload_for_hash = {k: v for k, v in rec.items() if k != "record_hash"}
                    expected = hash_chain_link(prev, payload_for_hash)
                    if rec["record_hash"] != expected:
                        raise AuditValidationError(
                            f"{path}:{lineno} record_hash mismatch: expected {expected}, "
                            f"got {rec['record_hash']}"
                        )
                    prev = rec["record_hash"]
                    count += 1

                    # cross-table ref tracking
                    rid = rec.get("run_id")
                    if rid:
                        if table is AuditTable.RUNS:
                            run_ids_seen.add(rid)
                        else:
                            ref_run_ids.add(rid)

            per_table_counts[table.value] = count

        dangling = ref_run_ids - run_ids_seen
        if dangling:
            raise AuditValidationError(f"dangling run_id refs (no runs.jsonl entry): {sorted(dangling)}")

        return per_table_counts

    @staticmethod
    def _check_record_shape(
        table: AuditTable, rec: dict, path: Path, lineno: int
    ) -> None:
        for field in (
            "schema_version",
            "created_at_utc",
            "research_boundary",
            "record_hash",
            "prev_record_hash",
            "table",
        ):
            if field not in rec:
                raise AuditValidationError(
                    f"{path}:{lineno} missing required field: {field}"
                )
        if rec["research_boundary"] != RESEARCH_BOUNDARY:
            raise AuditValidationError(
                f"{path}:{lineno} research_boundary string drift; canonical boundary required"
            )
        if rec["table"] != table.value:
            raise AuditValidationError(
                f"{path}:{lineno} table mismatch: file={table.value}, record table={rec['table']}"
            )

        # Boundary trip on free-form text fields
        text_blob = canonical_json(rec).lower()
        violations = boundary_violations(text_blob)
        if violations:
            raise AuditValidationError(
                f"{path}:{lineno} clinical-overclaim phrases present: {violations[:3]}"
            )

        # PHI / secrets markers
        for marker in _PHI_MARKERS:
            if marker in text_blob:
                raise AuditValidationError(f"{path}:{lineno} PHI marker present: {marker!r}")
        for marker in _SECRET_MARKERS:
            if marker in text_blob:
                raise AuditValidationError(f"{path}:{lineno} secret marker present: {marker!r}")

        # Bulk local reference markers (offload should be HF dataset, not local raw)
        if table is AuditTable.ARTIFACTS:
            p = str(rec.get("path", ""))
            for pat in _BULK_LOCAL_PATTERNS:
                if pat in p and not rec.get("offload_ref"):
                    raise AuditValidationError(
                        f"{path}:{lineno} bulk local artifact without offload_ref: {p}"
                    )

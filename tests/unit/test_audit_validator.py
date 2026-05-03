"""Comprehensive negative tests for AuditValidator.

Each test writes records that TRIP a specific validation rule, then asserts
that AuditValidationError is raised with the expected substring in the message.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_biomolecular_explorer.audit import (
    AuditValidationError,
    AuditValidator,
    AuditWriter,
    AuditTable,
)
from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
from zer0pa_biomolecular_explorer.hashing import GENESIS_HASH, canonical_json, hash_chain_link
from zer0pa_biomolecular_explorer.ids import audit_id, run_id


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _make_audit_dir(tmp_path: Path) -> tuple[Path, str, AuditWriter]:
    rid = run_id()
    audit_root = tmp_path / "audit"
    writer = AuditWriter(audit_root, rid)
    return audit_root, rid, writer


def _valid_run_record(run_id_val: str) -> dict:
    return {
        "table": "runs",
        "run_id": run_id_val,
        "executor_identity": "test_suite",
        "environment": {},
    }


def _valid_falsifier_record(run_id_val: str) -> dict:
    return {
        "table": "falsifiers",
        "run_id": run_id_val,
        "falsifier_id": f"falsifier:test:{run_id_val}",
        "falsifier_class": "herg_only_overreach",
        "layer_scope": ["L5"],
        "trigger_condition": "test trigger",
        "status": "pass",
        "evidence": [],
    }


def _valid_parameters_record(run_id_val: str) -> dict:
    return {
        "table": "parameters",
        "run_id": run_id_val,
        "layer": "L5",
        "adapter_id": "adapter:L5:test:v1",
        "parameters": {"lr": 0.001},
    }


def _valid_artifact_record(run_id_val: str) -> dict:
    return {
        "table": "artifacts",
        "run_id": run_id_val,
        "artifact_id": "artifact:test:001",
        "path": "/data/processed/small_output.json",
        "size_bytes": 1024,
        "content_hash": "sha256:" + "a" * 64,
    }


def _valid_molecules_record(run_id_val: str) -> dict:
    return {
        "table": "molecules",
        "run_id": run_id_val,
        "molecule_id": "molecule:inchikey:IXTMWRCNAAVVAI-UHFFFAOYSA-N",
        "inchikey": "IXTMWRCNAAVVAI-UHFFFAOYSA-N",
        "name": "dofetilide",
    }


def _valid_confidence_record(run_id_val: str) -> dict:
    return {
        "table": "confidence",
        "run_id": run_id_val,
        "envelope_id": f"envelope:L5:{run_id_val}",
        "layer": "L5",
        "score": 0.7,
        "band": "medium",
        "decomposition": {"channel_coverage": 0.8},
        "calibration_basis": ["stub_canned_outputs"],
    }


# ──────────────────────────────────────────────────────────────────────
# Test (a): PHI marker in evidence
# ──────────────────────────────────────────────────────────────────────


def test_phi_marker_in_falsifier_evidence(tmp_path):
    """PHI marker 'patient_name' in falsifier evidence must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    phi_record = {
        "table": "falsifiers",
        "run_id": rid,
        "falsifier_id": f"falsifier:test:{rid}",
        "falsifier_class": "clinical_overclaim",
        "layer_scope": ["L5"],
        "trigger_condition": "test PHI trigger",
        "status": "fail",
        "evidence": ["patient_name: jdoe was in the dataset"],
    }
    writer.append(AuditTable.FALSIFIERS, phi_record)

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="PHI marker"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (b): Secret marker in parameters
# ──────────────────────────────────────────────────────────────────────


def test_secret_marker_in_parameters(tmp_path):
    """Secret marker 'api_key=' in parameters must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    secret_record = {
        "table": "parameters",
        "run_id": rid,
        "layer": "L1",
        "adapter_id": "adapter:L1:test:v1",
        "parameters": {"api_key=secret123": "do_not_store"},
    }
    writer.append(AuditTable.PARAMETERS, secret_record)

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="secret marker"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (c): Bulk local artifact without offload_ref
# ──────────────────────────────────────────────────────────────────────


def test_bulk_local_artifact_without_offload_ref(tmp_path):
    """Artifact with path=/data/raw/big.parquet and no offload_ref must raise."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    artifact_record = {
        "table": "artifacts",
        "run_id": rid,
        "artifact_id": "artifact:test:bulk",
        "path": "/data/raw/big.parquet",
        "size_bytes": 500_000_000,
        "content_hash": "sha256:" + "b" * 64,
        # offload_ref intentionally absent
    }
    writer.append(AuditTable.ARTIFACTS, artifact_record)

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="bulk local artifact without offload_ref"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (d): Boundary string drift in runs record
# ──────────────────────────────────────────────────────────────────────


def test_boundary_string_drift(tmp_path):
    """Truncated research_boundary in a runs record must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    # Write a valid record first (so the run dir exists)
    # Then manually inject a corrupt record bypassing the writer's auto-stamp
    run_dir = audit_root / "runs" / rid
    run_dir.mkdir(parents=True, exist_ok=True)

    # Build a record with drifted boundary but valid hash chain
    bad_boundary = "Research only"
    payload: dict = {
        "table": "runs",
        "run_id": rid,
        "executor_identity": "test_suite",
        "environment": {},
        "schema_version": "v1",
        "created_at_utc": "2026-04-30T00:00:00Z",
        "research_boundary": bad_boundary,
    }
    prev = GENESIS_HASH
    payload["prev_record_hash"] = prev
    payload_for_hash = {k: v for k, v in payload.items() if k != "record_hash"}
    record_hash = hash_chain_link(prev, payload_for_hash)
    payload["record_hash"] = record_hash

    runs_path = run_dir / "runs.jsonl"
    with runs_path.open("w", encoding="utf-8") as fh:
        fh.write(canonical_json(payload) + "\n")

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="research_boundary string drift"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (e): Hash chain break
# ──────────────────────────────────────────────────────────────────────


def test_hash_chain_break(tmp_path):
    """Corrupting the second record's prev_record_hash must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))
    writer.append(AuditTable.RUNS, {
        "table": "runs",
        "run_id": run_id(),
        "executor_identity": "test_suite_second",
        "environment": {},
    })

    # Read the JSONL, corrupt the second record's prev_record_hash
    runs_path = audit_root / "runs" / rid / "runs.jsonl"
    lines = runs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec2 = json.loads(lines[1])
    rec2["prev_record_hash"] = "sha256:" + "0" * 64  # corrupt
    lines[1] = canonical_json(rec2)
    runs_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="prev_record_hash mismatch"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (f): Dangling run_id in molecules table
# ──────────────────────────────────────────────────────────────────────


def test_dangling_run_id(tmp_path):
    """A molecules record with a run_id not in runs.jsonl must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    ghost_run_id = "run:20260430-deadbeef"
    mol_record = {
        "table": "molecules",
        "run_id": ghost_run_id,  # not registered in runs.jsonl
        "molecule_id": "molecule:test:001",
        "name": "ghost_compound",
    }
    writer.append(AuditTable.MOLECULES, mol_record)

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="dangling run_id"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (g): Clinical overclaim phrase in confidence record
# ──────────────────────────────────────────────────────────────────────


def test_clinical_overclaim_phrase_in_confidence_record(tmp_path):
    """Clinical-overclaim phrase in a confidence record must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    overclaim_record = {
        "table": "confidence",
        "run_id": rid,
        "envelope_id": f"envelope:L5:{rid}",
        "layer": "L5",
        "score": 0.9,
        "band": "high",
        "decomposition": {"label": 0.9},
        "calibration_basis": ["this compound is fda approved for cardiac use"],
    }
    writer.append(AuditTable.CONFIDENCE, overclaim_record)

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="clinical-overclaim"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (h): Missing schema_version
# ──────────────────────────────────────────────────────────────────────


def test_missing_schema_version(tmp_path):
    """A record written without schema_version must raise AuditValidationError."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    # Manually inject a record that skips schema_version
    run_dir = audit_root / "runs" / rid
    run_dir.mkdir(parents=True, exist_ok=True)

    payload: dict = {
        "table": "runs",
        "run_id": rid,
        "executor_identity": "test_suite",
        "environment": {},
        # schema_version intentionally omitted
        "created_at_utc": "2026-04-30T00:00:00Z",
        "research_boundary": RESEARCH_BOUNDARY,
    }
    prev = GENESIS_HASH
    payload["prev_record_hash"] = prev
    payload_for_hash = {k: v for k, v in payload.items() if k != "record_hash"}
    record_hash = hash_chain_link(prev, payload_for_hash)
    payload["record_hash"] = record_hash

    runs_path = run_dir / "runs.jsonl"
    with runs_path.open("w", encoding="utf-8") as fh:
        fh.write(canonical_json(payload) + "\n")

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="missing required field"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (i): Record hash mismatch (tampered content)
# ──────────────────────────────────────────────────────────────────────


def test_record_hash_mismatch(tmp_path):
    """Tampering with a record's content (not the hash) must raise record_hash mismatch."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    runs_path = audit_root / "runs" / rid / "runs.jsonl"
    lines = runs_path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["executor_identity"] = "tampered_identity"  # change content without updating hash
    lines[0] = canonical_json(rec)
    runs_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    validator = AuditValidator(audit_root, rid)
    with pytest.raises(AuditValidationError, match="record_hash mismatch"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (j): Nonexistent run dir
# ──────────────────────────────────────────────────────────────────────


def test_nonexistent_run_dir_raises(tmp_path):
    """AuditValidator on a nonexistent run dir must raise AuditValidationError."""
    audit_root = tmp_path / "audit"
    audit_root.mkdir(parents=True, exist_ok=True)
    validator = AuditValidator(audit_root, "run:no-such-run-12345678")
    with pytest.raises(AuditValidationError, match="run dir does not exist"):
        validator.validate()


# ──────────────────────────────────────────────────────────────────────
# Test (k): Valid single record passes validation
# ──────────────────────────────────────────────────────────────────────


def test_valid_single_record_passes(tmp_path):
    """A single valid runs record must pass validation without raising."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))
    validator = AuditValidator(audit_root, rid)
    counts = validator.validate()
    assert counts.get("runs", 0) == 1


# ──────────────────────────────────────────────────────────────────────
# Test (l): Bulk local artifact WITH offload_ref passes validation
# ──────────────────────────────────────────────────────────────────────


def test_bulk_artifact_with_offload_ref_passes(tmp_path):
    """A bulk local artifact record WITH offload_ref must pass validation."""
    audit_root, rid, writer = _make_audit_dir(tmp_path)
    writer.append(AuditTable.RUNS, _valid_run_record(rid))

    artifact_record = {
        "table": "artifacts",
        "run_id": rid,
        "artifact_id": "artifact:test:offloaded",
        "path": "/data/raw/big.parquet",
        "size_bytes": 500_000_000,
        "content_hash": "sha256:" + "c" * 64,
        "offload_ref": "Architect-Prime/zer0pa-health-cardiac-v0:files/big.parquet",
    }
    writer.append(AuditTable.ARTIFACTS, artifact_record)

    validator = AuditValidator(audit_root, rid)
    counts = validator.validate()
    assert counts.get("artifacts", 0) == 1

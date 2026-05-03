"""Tests: ReasonerTuple Pydantic model accepts/rejects sample tuples
and JSON Schema validates against model_dump output.

PRD section 8 canonical schema verification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_biomolecular_explorer.ids import falsifier_id, tuple_id, utc_now_iso
from zer0pa_biomolecular_explorer.reasoner.tuple_schema import (
    AUTHORITY_ORDER,
    FORBIDDEN_OUTPUTS,
    REQUIRED_CAVEATS,
    GroundTruthStatus,
    GroundTruthType,
    KGEdgeProposal,
    NextAction,
    ReasonerFalsifierClass,
    ReasonerFalsifierStatus,
    ReasonerInput,
    ReasonerOutput,
    ReasonerTuple,
    TaskType,
    TupleAbstention,
    TupleAudit,
    TupleClaim,
    TupleConstraints,
    TupleEntities,
    TupleFalsifier,
    TupleGroundTruth,
)

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "reasoner" / "reasoner-tuple-v1.json"


# ---------------------------------------------------------------------------
# Fixture: minimal valid tuple dict
# ---------------------------------------------------------------------------


def _make_valid_tuple_dict() -> dict:
    fid = falsifier_id("source_conflict")
    cid = "claim:20260430-abcd1234"
    return {
        "tuple_id": "tuple:20260430-cafebabe",
        "schema_version": "reasoner_tuple.v1",
        "created_at_utc": "2026-04-30T00:00:00Z",
        "run_id": "run:20260430-deadbeef",
        "task_type": "evidence_packet",
        "input": {
            "question": "What is the multi-current cardiac risk profile of dofetilide?",
            "entities": {
                "compounds": ["dofetilide"],
                "genes": ["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
                "currents": ["IKr", "INa", "IKs", "ICaL"],
                "phenotypes": ["QTc prolongation"],
            },
            "context_pack_refs": ["source:20260430-aabbccdd"],
            "constraints": {
                "authority_order": AUTHORITY_ORDER,
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "required_caveats": REQUIRED_CAVEATS,
            },
        },
        "output": {
            "claims": [
                {
                    "claim_id": cid,
                    "text": "Research observation: dofetilide shows strong IKr inhibition in the cardiac channel panel. [research_only]",
                    "confidence": 0.85,
                    "source_refs": ["source:20260430-aabbccdd"],
                    "falsifier_ref": fid,
                    "multi_current_context": True,
                }
            ],
            "abstentions": [],
            "kg_edge_proposals": [
                {
                    "subject": "dofetilide",
                    "predicate": "MODULATES",
                    "object": "IKr",
                    "confidence": 0.85,
                    "source_ref": "source:20260430-aabbccdd",
                    "claim_ref": cid,
                }
            ],
            "next_actions": [
                {
                    "action": "attach_multi_current_context_pack",
                    "reason": "Cardiac entities present.",
                    "priority": "normal",
                }
            ],
        },
        "falsifier": {
            "falsifier_id": fid,
            "class": "source_conflict",
            "trigger_condition": "Routine source-conflict check; no violations detected.",
            "status": "passed",
        },
        "ground_truth": {
            "status": "available",
            "type": "source_anchor",
            "source_refs": ["source:20260430-aabbccdd"],
        },
        "audit": {
            "prompt_hash": "sha256:" + "a" * 64,
            "context_hash": "sha256:" + "b" * 64,
            "output_hash": "sha256:" + "c" * 64,
            "license_flags": ["A"],
        },
    }


# ---------------------------------------------------------------------------
# Acceptance tests
# ---------------------------------------------------------------------------


class TestReasonerTupleAccepts:
    def test_minimal_valid_tuple(self):
        d = _make_valid_tuple_dict()
        t = ReasonerTuple.model_validate(d)
        assert t.tuple_id == "tuple:20260430-cafebabe"
        assert t.schema_version == "reasoner_tuple.v1"
        assert t.task_type == TaskType.EVIDENCE_PACKET
        assert len(t.output.claims) == 1
        assert t.output.claims[0].multi_current_context is True
        assert t.output.claims[0].falsifier_ref.startswith("falsifier:")

    def test_all_task_types_accepted(self):
        for tt in TaskType:
            d = _make_valid_tuple_dict()
            d["task_type"] = tt.value
            t = ReasonerTuple.model_validate(d)
            assert t.task_type == tt

    def test_all_falsifier_classes_accepted(self):
        for fc in ReasonerFalsifierClass:
            d = _make_valid_tuple_dict()
            d["falsifier"]["class"] = fc.value
            t = ReasonerTuple.model_validate(d)
            assert t.falsifier.falsifier_class == fc

    def test_all_falsifier_statuses_accepted(self):
        for fs in ReasonerFalsifierStatus:
            d = _make_valid_tuple_dict()
            d["falsifier"]["status"] = fs.value
            t = ReasonerTuple.model_validate(d)
            assert t.falsifier.status == fs

    def test_all_ground_truth_statuses_accepted(self):
        for gts in GroundTruthStatus:
            d = _make_valid_tuple_dict()
            d["ground_truth"]["status"] = gts.value
            if gts == GroundTruthStatus.NOT_APPLICABLE:
                d["ground_truth"]["type"] = None
            t = ReasonerTuple.model_validate(d)
            assert t.ground_truth.status == gts

    def test_empty_claims_and_abstentions_accepted(self):
        d = _make_valid_tuple_dict()
        d["output"]["claims"] = []
        d["output"]["abstentions"] = [
            {"entity": "dofetilide", "reason": "no context pack", "evidence_gap": "empty refs"}
        ]
        t = ReasonerTuple.model_validate(d)
        assert t.output.claims == []
        assert len(t.output.abstentions) == 1

    def test_model_dump_roundtrip(self):
        d = _make_valid_tuple_dict()
        t = ReasonerTuple.model_validate(d)
        dumped = json.loads(t.model_dump_json(by_alias=True))
        t2 = ReasonerTuple.model_validate(dumped)
        assert t2.tuple_id == t.tuple_id
        assert t2.schema_version == "reasoner_tuple.v1"


# ---------------------------------------------------------------------------
# Rejection tests
# ---------------------------------------------------------------------------


class TestReasonerTupleRejects:
    def test_rejects_bad_tuple_id_prefix(self):
        d = _make_valid_tuple_dict()
        d["tuple_id"] = "bad:20260430-cafebabe"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_bad_run_id_prefix(self):
        d = _make_valid_tuple_dict()
        d["run_id"] = "not-a-run-id"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_wrong_schema_version(self):
        d = _make_valid_tuple_dict()
        d["schema_version"] = "reasoner_tuple.v2"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_invalid_task_type(self):
        d = _make_valid_tuple_dict()
        d["task_type"] = "hallucination_sprint"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_invalid_falsifier_class(self):
        d = _make_valid_tuple_dict()
        d["falsifier"]["class"] = "stub_laundering"  # envelope class, not reasoner class
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_clinical_overclaim_in_claim_text(self):
        d = _make_valid_tuple_dict()
        d["output"]["claims"][0]["text"] = "dofetilide is fda approved for atrial fibrillation"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_missing_falsifier_ref(self):
        d = _make_valid_tuple_dict()
        d["output"]["claims"][0]["falsifier_ref"] = ""
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_hash_without_prefix(self):
        d = _make_valid_tuple_dict()
        d["audit"]["prompt_hash"] = "abc123"  # missing sha256: prefix
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_extra_fields(self):
        d = _make_valid_tuple_dict()
        d["surprise_field"] = "not allowed"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_missing_forbidden_outputs(self):
        d = _make_valid_tuple_dict()
        d["input"]["constraints"]["forbidden_outputs"] = ["diagnosis"]  # incomplete
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_missing_required_caveats(self):
        d = _make_valid_tuple_dict()
        d["input"]["constraints"]["required_caveats"] = ["research_only"]  # incomplete
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_clinical_overclaim_in_question(self):
        d = _make_valid_tuple_dict()
        d["input"]["question"] = "is dofetilide fda approved for cardiac use?"
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)

    def test_rejects_confidence_out_of_range(self):
        d = _make_valid_tuple_dict()
        d["output"]["claims"][0]["confidence"] = 1.5
        with pytest.raises(Exception):
            ReasonerTuple.model_validate(d)


# ---------------------------------------------------------------------------
# JSON Schema validation
# ---------------------------------------------------------------------------


class TestJsonSchemaValidation:
    def _load_schema(self) -> dict:
        assert SCHEMA_PATH.exists(), f"JSON schema not found at {SCHEMA_PATH}"
        with SCHEMA_PATH.open() as f:
            return json.load(f)

    def test_schema_file_exists(self):
        schema = self._load_schema()
        assert schema["$id"] == "zer0pa:reasoner-tuple-v1"
        assert schema["title"] == "ReasonerTuple"

    def test_schema_has_all_required_top_level_fields(self):
        schema = self._load_schema()
        required = set(schema["required"])
        expected = {"tuple_id", "schema_version", "created_at_utc", "run_id", "task_type",
                    "input", "output", "falsifier", "ground_truth", "audit"}
        assert expected.issubset(required)

    def test_schema_task_type_enum_matches_pydantic(self):
        schema = self._load_schema()
        schema_enums = set(schema["properties"]["task_type"]["enum"])
        pydantic_enums = {tt.value for tt in TaskType}
        assert schema_enums == pydantic_enums

    def test_schema_falsifier_class_enum_matches_pydantic(self):
        schema = self._load_schema()
        schema_enums = set(schema["properties"]["falsifier"]["properties"]["class"]["enum"])
        pydantic_enums = {fc.value for fc in ReasonerFalsifierClass}
        assert schema_enums == pydantic_enums

    def test_schema_falsifier_status_enum_matches_pydantic(self):
        schema = self._load_schema()
        schema_enums = set(schema["properties"]["falsifier"]["properties"]["status"]["enum"])
        pydantic_enums = {fs.value for fs in ReasonerFalsifierStatus}
        assert schema_enums == pydantic_enums

    def test_schema_ground_truth_status_enum_matches_pydantic(self):
        schema = self._load_schema()
        schema_enums = set(schema["properties"]["ground_truth"]["properties"]["status"]["enum"])
        pydantic_enums = {gts.value for gts in GroundTruthStatus}
        assert schema_enums == pydantic_enums

    def test_model_dump_matches_schema_structure(self):
        """Verify that a model_dump() of a valid tuple has the required keys at each level."""
        d = _make_valid_tuple_dict()
        t = ReasonerTuple.model_validate(d)
        dumped = json.loads(t.model_dump_json(by_alias=True))

        schema = self._load_schema()
        # Top-level required fields
        for field in schema["required"]:
            assert field in dumped, f"model_dump missing required field: {field}"

        # Input required fields
        for field in schema["properties"]["input"]["required"]:
            assert field in dumped["input"], f"input missing field: {field}"

        # Falsifier required fields
        for field in schema["properties"]["falsifier"]["required"]:
            assert field in dumped["falsifier"], f"falsifier missing field: {field}"

        # Audit required fields
        for field in schema["properties"]["audit"]["required"]:
            assert field in dumped["audit"], f"audit missing field: {field}"

    def test_schema_no_additionalproperties_at_root(self):
        schema = self._load_schema()
        assert schema.get("additionalProperties") is False

    def test_schema_has_correct_schema_version_const(self):
        schema = self._load_schema()
        assert schema["properties"]["schema_version"]["const"] == "reasoner_tuple.v1"

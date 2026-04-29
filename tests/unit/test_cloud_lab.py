"""Unit tests for cloud-lab adapter stubs (PRD section 9).

Tests cover:
- default_config() matches PRD specs.
- StrateosStub.submit() raises NetworkSubmitDisabledError when allow_network_submit=False.
- StrateosStub.submit() raises BlockedClassError for blocked protocol classes
  even when allow_network_submit=True and token is provided.
- EmeraldStub.validate_protocol() rejects clinical-overclaim boundary phrases.
- ArctorisStub.quote() is deterministic (same protocol -> same cost).
- check_approval_token('', required=True) returns False.
- check_blocked_class with autonomous wet lab execution text returns (True, ...).
- Protocol interface structural compliance (all three stubs).
- poll_status returns dry_run_only.
- fetch_results always raises in dry-run mode.
- stage() returns a staging_id.
- capabilities() includes stub=True flag.
"""

from __future__ import annotations

import pytest

from zer0pa_health.cloud_lab import (
    ArctorisStub,
    BudgetExceededError,
    CloudLabAdapter,
    EmeraldStub,
    NetworkSubmitDisabledError,
    StrateosStub,
    ApprovalTokenRequiredError,
    BlockedClassError,
    default_config,
)
from zer0pa_health.cloud_lab.config import CloudLabConfig
from zer0pa_health.cloud_lab.interlocks import (
    check_approval_token,
    check_blocked_class,
    check_boundary_in_protocol,
    check_budget,
    check_network_submit_disabled,
)


# ---------------------------------------------------------------------------
# default_config() tests (PRD section 9)
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    def test_enabled_false(self):
        cfg = default_config()
        assert cfg.enabled is False

    def test_mode_dry_run(self):
        cfg = default_config()
        assert cfg.mode == "dry_run"

    def test_allow_network_submit_false(self):
        cfg = default_config()
        assert cfg.allow_network_submit is False

    def test_max_budget_usd_zero(self):
        cfg = default_config()
        assert cfg.max_budget_usd == 0.0

    def test_require_user_approval_token_true(self):
        cfg = default_config()
        assert cfg.require_user_approval_token is True

    def test_vendor_none(self):
        cfg = default_config()
        assert cfg.vendor == "none"

    def test_blocked_classes_contains_prd_defaults(self):
        cfg = default_config()
        expected = [
            "clinical",
            "human_diagnosis",
            "treatment",
            "prescribing",
            "regulated_safety_certification",
            "PHI",
            "controlled_or_hazardous_material",
            "autonomous_wet_lab_execution",
        ]
        for cls in expected:
            assert cls in cfg.blocked_classes, f"Missing blocked class: {cls}"

    def test_returns_cloudlabconfig_instance(self):
        cfg = default_config()
        assert isinstance(cfg, CloudLabConfig)


# ---------------------------------------------------------------------------
# StrateosStub tests
# ---------------------------------------------------------------------------


class TestStrateosStub:
    def test_submit_raises_network_submit_disabled_by_default(self):
        """StrateosStub.submit() must raise NetworkSubmitDisabledError when
        allow_network_submit=False (the DEFAULT configuration)."""
        stub = StrateosStub()  # uses default_config()
        with pytest.raises(NetworkSubmitDisabledError):
            stub.submit({"assay_type": "biochemical_ic50"}, approval_token="valid-token-xyz")

    def test_submit_raises_network_submit_disabled_explicit(self):
        """Explicit allow_network_submit=False also blocks submit."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="dry_run",
            allow_network_submit=False,
            max_budget_usd=500.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)
        with pytest.raises(NetworkSubmitDisabledError):
            stub.submit({"assay_type": "sbs_plate_screening"}, approval_token="tok123")

    def test_submit_blocked_class_raises_even_with_network_enabled(self):
        """Even when allow_network_submit=True and token is valid,
        a protocol containing a blocked class (e.g. 'clinical') must raise BlockedClassError."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=5000.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)

        # Protocol with 'clinical' — a blocked class
        protocol = {"assay_type": "biochemical_ic50", "notes": "clinical trial compound"}
        with pytest.raises(BlockedClassError):
            stub.submit(protocol, approval_token="valid-token-abc")

    def test_submit_blocked_class_phi(self):
        """PHI in protocol triggers BlockedClassError."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=5000.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)
        protocol = {"assay_type": "protein_binding_assay", "sample_id": "PHI_patient_123"}
        with pytest.raises(BlockedClassError):
            stub.submit(protocol, approval_token="valid-token-abc")

    def test_submit_blocked_class_treatment(self):
        """'treatment' in protocol triggers BlockedClassError."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=5000.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)
        protocol = {"purpose": "drug treatment selection for patient"}
        with pytest.raises(BlockedClassError):
            stub.submit(protocol, approval_token="valid-token-abc")

    def test_submit_blocked_class_diagnose(self):
        """'diagnose' triggers BlockedClassError via human_diagnosis? No — 'diagnose'
        is not in the default list, but 'human_diagnosis' is. Test 'human_diagnosis'."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=5000.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)
        protocol = {"purpose": "human_diagnosis support assay"}
        with pytest.raises(BlockedClassError):
            stub.submit(protocol, approval_token="valid-token-abc")

    def test_submit_missing_token_raises_approval_required(self):
        """Empty token raises ApprovalTokenRequiredError before network gate."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=5000.0,
            require_user_approval_token=True,
        )
        stub = StrateosStub(config=cfg)
        with pytest.raises(ApprovalTokenRequiredError):
            stub.submit({"assay_type": "biochemical_ic50"}, approval_token="")

    def test_capabilities_has_stub_true(self):
        stub = StrateosStub()
        caps = stub.capabilities()
        assert caps["stub"] is True
        assert caps["vendor"] == "strateos"

    def test_capabilities_lists_assay_types(self):
        stub = StrateosStub()
        caps = stub.capabilities()
        assert "supported_assay_types" in caps
        assert len(caps["supported_assay_types"]) > 0

    def test_poll_status_returns_dry_run_only(self):
        stub = StrateosStub()
        result = stub.poll_status("strateos:job:abc123")
        assert result["status"] == "dry_run_only"
        assert result["vendor"] == "strateos"

    def test_fetch_results_raises(self):
        stub = StrateosStub()
        with pytest.raises(RuntimeError, match="dry-run mode"):
            stub.fetch_results("strateos:job:abc123")

    def test_stage_returns_staging_id(self):
        stub = StrateosStub()
        result = stub.stage({"assay_type": "biochemical_ic50"})
        assert "staging_id" in result
        assert result["staging_id"].startswith("strateos:staging:")

    def test_validate_protocol_clean(self):
        stub = StrateosStub()
        result = stub.validate_protocol({"assay_type": "biochemical_ic50", "compound": "dofetilide"})
        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_protocol_blocked_class(self):
        stub = StrateosStub()
        result = stub.validate_protocol({"assay_type": "clinical_trial_screening"})
        assert result["valid"] is False
        assert len(result["issues"]) > 0


# ---------------------------------------------------------------------------
# EmeraldStub tests
# ---------------------------------------------------------------------------


class TestEmeraldStub:
    def test_validate_protocol_rejects_clinical_overclaim(self):
        """EmeraldStub.validate_protocol() must reject protocols containing
        clinical-overclaim boundary phrases (PRD section 9)."""
        stub = EmeraldStub()

        # Use an actual CLINICAL_OVERCLAIM_PHRASES entry from boundary.py
        protocol = {
            "assay_type": "itc_binding_thermodynamics",
            "notes": "This compound is safe for patients based on our ITC data.",
        }
        result = stub.validate_protocol(protocol)
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert any("clinical-overclaim" in issue for issue in result["issues"])

    def test_validate_protocol_rejects_fda_approved_phrase(self):
        stub = EmeraldStub()
        protocol = {"notes": "compound is FDA-approved for cardiac use"}
        result = stub.validate_protocol(protocol)
        assert result["valid"] is False

    def test_validate_protocol_rejects_should_be_prescribed(self):
        stub = EmeraldStub()
        protocol = {"notes": "should be prescribed at 10mg daily"}
        result = stub.validate_protocol(protocol)
        assert result["valid"] is False

    def test_validate_protocol_rejects_blocked_class(self):
        stub = EmeraldStub()
        protocol = {"purpose": "PHI compound profiling"}
        result = stub.validate_protocol(protocol)
        assert result["valid"] is False

    def test_validate_protocol_passes_clean(self):
        stub = EmeraldStub()
        protocol = {"assay_type": "nmr_1h", "compound": "ranolazine", "concentration_mm": 1.0}
        result = stub.validate_protocol(protocol)
        assert result["valid"] is True
        assert result["issues"] == []

    def test_capabilities_vendor_emerald(self):
        stub = EmeraldStub()
        caps = stub.capabilities()
        assert caps["vendor"] == "emerald"
        assert caps["stub"] is True

    def test_capabilities_has_nmr(self):
        """Emerald specifically supports NMR — vendor differentiation."""
        stub = EmeraldStub()
        caps = stub.capabilities()
        assert any("nmr" in a for a in caps["supported_assay_types"])

    def test_submit_raises_network_disabled_by_default(self):
        stub = EmeraldStub()
        with pytest.raises(NetworkSubmitDisabledError):
            stub.submit({"assay_type": "nmr_1h"}, approval_token="tok")

    def test_poll_status_dry_run_only(self):
        stub = EmeraldStub()
        result = stub.poll_status("emerald:job:xyz")
        assert result["status"] == "dry_run_only"

    def test_fetch_results_raises(self):
        stub = EmeraldStub()
        with pytest.raises(RuntimeError, match="dry-run mode"):
            stub.fetch_results("emerald:job:xyz")


# ---------------------------------------------------------------------------
# ArctorisStub tests
# ---------------------------------------------------------------------------


class TestArctorisStub:
    def test_quote_deterministic(self):
        """ArctorisStub.quote() must be deterministic: same protocol -> same cost."""
        stub = ArctorisStub()
        protocol = {"assay_type": "herg_qpatch_automated_patch_clamp", "compound": "dofetilide"}
        result1 = stub.quote(protocol)
        result2 = stub.quote(protocol)
        assert result1["estimated_cost_usd"] == result2["estimated_cost_usd"]
        assert result1["lead_time_h"] == result2["lead_time_h"]

    def test_quote_different_protocols_differ(self):
        """Different protocols should produce different (or potentially same) costs —
        we verify determinism specifically, but also that the function runs cleanly."""
        stub = ArctorisStub()
        p1 = {"assay_type": "herg_qpatch_automated_patch_clamp", "compound": "dofetilide"}
        p2 = {"assay_type": "cytotoxicity_mtt", "compound": "verapamil"}
        r1 = stub.quote(p1)
        r2 = stub.quote(p2)
        # Both must have the required keys
        for key in ("estimated_cost_usd", "lead_time_h", "blocked", "blocked_reason"):
            assert key in r1
            assert key in r2

    def test_quote_blocked_protocol(self):
        """A blocked-class protocol returns blocked=True in quote."""
        stub = ArctorisStub()
        protocol = {"assay_type": "clinical_compound_screening"}
        result = stub.quote(protocol)
        assert result["blocked"] is True
        assert result["blocked_reason"] is not None

    def test_quote_clean_protocol_not_blocked(self):
        stub = ArctorisStub()
        protocol = {"assay_type": "herg_qpatch_automated_patch_clamp", "compound": "ranolazine"}
        result = stub.quote(protocol)
        assert result["blocked"] is False
        assert result["blocked_reason"] is None

    def test_capabilities_vendor_arctoris(self):
        stub = ArctorisStub()
        caps = stub.capabilities()
        assert caps["vendor"] == "arctoris"
        assert caps["stub"] is True

    def test_capabilities_has_herg_assay(self):
        """Arctoris specifically includes hERG patch-clamp — vendor differentiation."""
        stub = ArctorisStub()
        caps = stub.capabilities()
        assert any("herg" in a for a in caps["supported_assay_types"])

    def test_submit_raises_network_disabled_by_default(self):
        stub = ArctorisStub()
        with pytest.raises(NetworkSubmitDisabledError):
            stub.submit({"assay_type": "herg_qpatch_automated_patch_clamp"}, approval_token="tok")

    def test_poll_status_dry_run_only(self):
        stub = ArctorisStub()
        result = stub.poll_status("arctoris:job:abc")
        assert result["status"] == "dry_run_only"

    def test_fetch_results_raises(self):
        stub = ArctorisStub()
        with pytest.raises(RuntimeError, match="dry-run mode"):
            stub.fetch_results("arctoris:job:abc")

    def test_stage_returns_staging_id(self):
        stub = ArctorisStub()
        result = stub.stage({"assay_type": "cyp_inhibition_panel"})
        assert result["staging_id"].startswith("arctoris:staging:")


# ---------------------------------------------------------------------------
# Interlock function unit tests
# ---------------------------------------------------------------------------


class TestInterlocks:
    def test_check_approval_token_empty_required(self):
        """check_approval_token('', required=True) must return False."""
        assert check_approval_token("", required=True) is False

    def test_check_approval_token_none_required(self):
        """check_approval_token(None, required=True) must return False."""
        assert check_approval_token(None, required=True) is False

    def test_check_approval_token_whitespace_required(self):
        """Whitespace-only token is invalid."""
        assert check_approval_token("   ", required=True) is False

    def test_check_approval_token_valid(self):
        assert check_approval_token("tok-abc-123", required=True) is True

    def test_check_approval_token_not_required(self):
        """When not required, any value (including empty) passes."""
        assert check_approval_token("", required=False) is True
        assert check_approval_token(None, required=False) is True

    def test_check_blocked_class_autonomous_wet_lab(self):
        """check_blocked_class with 'autonomous wet lab execution' text returns (True, ...)."""
        from zer0pa_health.cloud_lab.config import default_config
        blocked_list = default_config().blocked_classes
        text = "autonomous wet lab execution of compound X in the target screening"
        result_blocked, result_reason = check_blocked_class(text, blocked_list)
        assert result_blocked is True
        assert result_reason is not None
        assert len(result_reason) > 0

    def test_check_blocked_class_clinical(self):
        blocked_list = ["clinical", "PHI", "treatment"]
        blocked, reason = check_blocked_class("this is a clinical assay", blocked_list)
        assert blocked is True
        assert "clinical" in reason.lower()

    def test_check_blocked_class_phi_uppercase(self):
        """PHI match is case-insensitive."""
        blocked_list = ["PHI"]
        blocked, reason = check_blocked_class("sample_id: phi_patient_001", blocked_list)
        assert blocked is True

    def test_check_blocked_class_clean(self):
        blocked_list = ["clinical", "PHI", "treatment"]
        blocked, reason = check_blocked_class("herg qpatch compound profiling", blocked_list)
        assert blocked is False
        assert reason is None

    def test_check_network_submit_disabled_raises(self):
        with pytest.raises(NetworkSubmitDisabledError):
            check_network_submit_disabled(allow=False)

    def test_check_network_submit_disabled_allows(self):
        """Does not raise when allow=True."""
        check_network_submit_disabled(allow=True)  # should not raise

    def test_check_budget_exceeded(self):
        with pytest.raises(BudgetExceededError):
            check_budget(estimated_usd=150.0, max_usd=100.0)

    def test_check_budget_at_limit(self):
        """Exactly at limit is allowed."""
        check_budget(estimated_usd=100.0, max_usd=100.0)  # should not raise

    def test_check_budget_zero_max_blocks_any_cost(self):
        """max_budget_usd=0.0 blocks any positive cost (PRD default)."""
        with pytest.raises(BudgetExceededError):
            check_budget(estimated_usd=0.01, max_usd=0.0)

    def test_check_boundary_in_protocol_overclaim(self):
        text = "This compound is safe for patients based on our data."
        assert check_boundary_in_protocol(text) is True

    def test_check_boundary_in_protocol_clean(self):
        text = "hERG IC50 profiling for compound dofetilide, research use only."
        assert check_boundary_in_protocol(text) is False


# ---------------------------------------------------------------------------
# Protocol structural compliance (isinstance check via runtime_checkable)
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Verify all three stubs satisfy the CloudLabAdapter structural Protocol."""

    def test_strateos_is_cloudlab_adapter(self):
        stub = StrateosStub()
        assert isinstance(stub, CloudLabAdapter)

    def test_emerald_is_cloudlab_adapter(self):
        stub = EmeraldStub()
        assert isinstance(stub, CloudLabAdapter)

    def test_arctoris_is_cloudlab_adapter(self):
        stub = ArctorisStub()
        assert isinstance(stub, CloudLabAdapter)


# ---------------------------------------------------------------------------
# Closed-loop pattern: failed wet-lab -> falsifier update
# ---------------------------------------------------------------------------


class TestClosedLoopPattern:
    """Verify the closed-loop pattern anchor points are in place.

    PRD section 9 step 6: Failed wet-lab results update falsifiers.
    They are not narrated as success.

    The cloud-lab adapters themselves do not update falsifiers directly —
    that is done by the caller (L6 / orchestration) after fetch_results().
    These tests verify that:
    - fetch_results() always raises in dry-run (no silent success narration)
    - poll_status() returns a non-success status in dry-run mode
    - The BlockedClassError chain prevents clinical boundary violations
      from silently reaching the submission layer.
    """

    def test_fetch_results_never_narrates_success_in_dry_run(self):
        """Dry-run fetch_results raises — cannot be accidentally narrated as success."""
        for stub in [StrateosStub(), EmeraldStub(), ArctorisStub()]:
            with pytest.raises(RuntimeError, match="dry-run mode"):
                stub.fetch_results("job:test-123")

    def test_poll_status_signals_dry_run_not_completed(self):
        """poll_status must not return 'completed' or 'success' in dry-run mode."""
        for stub in [StrateosStub(), EmeraldStub(), ArctorisStub()]:
            result = stub.poll_status("job:test-123")
            assert result["status"] == "dry_run_only"
            assert result["status"] not in ("completed", "success", "done")

    def test_blocked_class_raises_before_submit(self):
        """BlockedClassError prevents 'clinical' protocol from being narrated as submitted."""
        cfg = CloudLabConfig(
            enabled=True,
            mode="real",
            allow_network_submit=True,
            max_budget_usd=9999.0,
            require_user_approval_token=True,
        )
        for stub in [StrateosStub(config=cfg), EmeraldStub(config=cfg), ArctorisStub(config=cfg)]:
            with pytest.raises(BlockedClassError):
                stub.submit(
                    {"purpose": "clinical deployment study"},
                    approval_token="valid-tok-xyz",
                )

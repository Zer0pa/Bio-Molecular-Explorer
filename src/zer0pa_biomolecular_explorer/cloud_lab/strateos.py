"""StrateosStub — dry-run adapter for Strateos cloud lab (PRD section 9).

Strateos focuses on automated small-molecule and biochemical assays with
strong SBS-plate automation. No real network calls are made.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from zer0pa_biomolecular_explorer.cloud_lab.config import CloudLabConfig, default_config
from zer0pa_biomolecular_explorer.cloud_lab.interlocks import (
    ApprovalTokenRequiredError,
    BlockedClassError,
    BudgetExceededError,
    NetworkSubmitDisabledError,
    check_approval_token,
    check_blocked_class,
    check_boundary_in_protocol,
    check_budget,
    check_network_submit_disabled,
)


class StrateosStub:
    """Strateos dry-run stub implementing CloudLabAdapter (PRD section 9).

    Vendor specialisation: Strateos provides automated liquid-handling,
    SBS-plate biochemical assays, and small-molecule screening workflows.
    All costs and timings are deterministic stubs based on protocol hash.
    """

    VENDOR = "strateos"

    # Strateos-specific stub assay capabilities
    _SUPPORTED_ASSAY_TYPES: list[str] = [
        "biochemical_ic50",
        "biochemical_ki",
        "sbs_plate_screening",
        "automated_liquid_handling",
        "absorbance_plate_reader",
        "fluorescence_plate_reader",
        "luminescence_plate_reader",
        "protein_binding_assay",
        "small_molecule_solubility",
    ]

    def __init__(self, config: CloudLabConfig | None = None) -> None:
        self.config = config if config is not None else default_config()

    def capabilities(self) -> dict:
        """Return Strateos stub capabilities.

        STUB flag is always True in dry-run mode. Lists supported
        small-molecule biochemical assay types.
        """
        return {
            "vendor": self.VENDOR,
            "stub": True,
            "mode": self.config.mode,
            "enabled": self.config.enabled,
            "supported_assay_types": self._SUPPORTED_ASSAY_TYPES,
            "automation_platform": "strateos_workcell",
            "plate_format": "SBS_384_96",
            "throughput": "medium_to_high",
            "note": (
                "Strateos stub: deterministic dry-run only. "
                "No real Strateos network calls are made."
            ),
        }

    def validate_protocol(self, protocol: dict) -> dict:
        """Run all interlocks and return {valid, issues}.

        Checks blocked classes and boundary violations.
        """
        issues: list[str] = []
        protocol_text = json.dumps(protocol)

        # Check blocked classes
        blocked, reason = check_blocked_class(protocol_text, self.config.blocked_classes)
        if blocked and reason:
            issues.append(reason)

        # Check clinical-overclaim boundary phrases
        if check_boundary_in_protocol(protocol_text):
            issues.append(
                "Protocol text contains clinical-overclaim phrases that violate "
                "the research boundary (PRD section 9)."
            )

        return {"valid": len(issues) == 0, "issues": issues}

    def quote(self, protocol: dict) -> dict:
        """Return a deterministic stub quote based on protocol hash.

        Same protocol dict always returns the same cost and lead time.
        """
        protocol_text = json.dumps(protocol, sort_keys=True)
        digest = hashlib.sha256(protocol_text.encode()).hexdigest()

        # Deterministic cost: 2 hex digits -> float in [10, 265]
        cost_seed = int(digest[0:2], 16)  # 0..255
        cost_usd = round(10.0 + cost_seed, 2)

        # Deterministic lead time: next 2 hex digits -> float in [24, 279]
        time_seed = int(digest[2:4], 16)  # 0..255
        lead_time_h = round(24.0 + time_seed, 1)

        # Check blocked class for the quote
        protocol_text_raw = json.dumps(protocol)
        blocked, blocked_reason = check_blocked_class(
            protocol_text_raw, self.config.blocked_classes
        )

        return {
            "estimated_cost_usd": cost_usd,
            "lead_time_h": lead_time_h,
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "vendor": self.VENDOR,
            "stub": True,
        }

    def stage(self, protocol: dict) -> dict:
        """Stage the protocol and return a stub staging ID.

        Does NOT submit to the Strateos network.
        """
        protocol_text = json.dumps(protocol, sort_keys=True)
        digest = hashlib.sha256(protocol_text.encode()).hexdigest()[:12]
        staging_id = f"strateos:staging:{digest}"
        staged_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "staging_id": staging_id,
            "staged_at": staged_at,
            "vendor": self.VENDOR,
            "mode": self.config.mode,
            "stub": True,
        }

    def submit(self, protocol: dict, approval_token: str) -> dict:
        """Attempt submission with full interlock chain.

        Interlock order (PRD section 9):
        1. Check approval token.
        2. Check network submit gate.
        3. Check blocked classes.
        4. Check budget.

        Raises:
            ApprovalTokenRequiredError: Token invalid when required.
            NetworkSubmitDisabledError: allow_network_submit=False (DEFAULT).
            BlockedClassError: Blocked class found in protocol.
            BudgetExceededError: Cost exceeds max_budget_usd.
        """
        # 1. Approval token check
        if not check_approval_token(approval_token, self.config.require_user_approval_token):
            raise ApprovalTokenRequiredError(
                "A valid user approval token is required before submission "
                "(require_user_approval_token=True). Provide a non-empty token."
            )

        # 2. Network submit gate — hard interlock
        check_network_submit_disabled(self.config.allow_network_submit)

        # 3. Blocked class check
        protocol_text = json.dumps(protocol)
        blocked, reason = check_blocked_class(protocol_text, self.config.blocked_classes)
        if blocked and reason:
            raise BlockedClassError(reason)

        # 4. Budget check
        quote = self.quote(protocol)
        check_budget(quote["estimated_cost_usd"], self.config.max_budget_usd)

        # If all interlocks pass (real mode only):
        protocol_text_sorted = json.dumps(protocol, sort_keys=True)
        digest = hashlib.sha256(protocol_text_sorted.encode()).hexdigest()[:12]
        job_id = f"strateos:job:{digest}"

        return {
            "job_id": job_id,
            "vendor": self.VENDOR,
            "status": "submitted",
            "stub": True,
        }

    def poll_status(self, job_id: str) -> dict:
        """Return dry-run-only status (PRD: no real results in stub mode)."""
        return {
            "job_id": job_id,
            "status": "dry_run_only",
            "vendor": self.VENDOR,
            "stub": True,
        }

    def fetch_results(self, job_id: str) -> dict:
        """Always raises in dry-run mode.

        Raises:
            RuntimeError: Always raised — dry-run mode produces no real results.
        """
        raise RuntimeError(
            f"dry-run mode: no real results to fetch for job_id={job_id!r}. "
            "Strateos stub does not produce real assay data."
        )

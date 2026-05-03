"""ArctorisStub — dry-run adapter for Arctoris cloud lab (PRD section 9).

Arctoris specialises in ADMET profiling, cell-based assays, and pharmacological
panel screening. No real network calls are made.
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


class ArctorisStub:
    """Arctoris dry-run stub implementing CloudLabAdapter (PRD section 9).

    Vendor specialisation: Arctoris provides ADMET profiling (DMPK, toxicology),
    cell-based assays (cytotoxicity, target engagement), in-vitro pharmacology
    panels (ion channel, GPCR, kinase), and automated compound management.
    Particularly relevant for hERG/ion-channel screening in the cardiac pipeline.
    """

    VENDOR = "arctoris"

    # Arctoris-specific stub assay capabilities — ADMET and pharmacology focus
    _SUPPORTED_ASSAY_TYPES: list[str] = [
        "herg_qpatch_automated_patch_clamp",
        "ion_channel_panel_screening",
        "nav_channel_assay",
        "cav_channel_assay",
        "cytotoxicity_mtt",
        "cytotoxicity_ctg",
        "metabolic_stability_microsomal",
        "plasma_protein_binding",
        "caco2_permeability",
        "cyp_inhibition_panel",
        "genotoxicity_ames",
        "kinase_selectivity_panel",
        "gpcr_binding_panel",
        "compound_management",
    ]

    def __init__(self, config: CloudLabConfig | None = None) -> None:
        self.config = config if config is not None else default_config()

    def capabilities(self) -> dict:
        """Return Arctoris stub capabilities.

        STUB flag is always True in dry-run mode. Lists ADMET and ion-channel
        assay types distinctive to Arctoris, especially relevant for CiPA/hERG.
        """
        return {
            "vendor": self.VENDOR,
            "stub": True,
            "mode": self.config.mode,
            "enabled": self.config.enabled,
            "supported_assay_types": self._SUPPORTED_ASSAY_TYPES,
            "automation_platform": "arctoris_autonomous_lab",
            "specialty": "ADMET_and_pharmacology_panels",
            "ion_channel_capability": "QPatch_automated_patch_clamp",
            "throughput": "medium_to_high",
            "note": (
                "Arctoris stub: deterministic dry-run only. "
                "No real Arctoris network calls are made. "
                "Arctoris is preferred for hERG/ion-channel profiling in cardiac pipeline."
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

        Arctoris tends toward moderate cost with fast turnaround for panel screens.
        Same protocol dict always returns the same cost and lead time.
        """
        protocol_text = json.dumps(protocol, sort_keys=True)
        digest = hashlib.sha256(protocol_text.encode()).hexdigest()

        # Deterministic cost: moderate base for ADMET panels
        cost_seed = int(digest[0:2], 16)  # 0..255
        cost_usd = round(15.0 + cost_seed * 0.8, 2)  # Arctoris: moderate cost

        # Lead time: faster than Emerald for panel screens
        time_seed = int(digest[2:4], 16)  # 0..255
        lead_time_h = round(36.0 + time_seed * 0.3, 1)  # Arctoris: faster turnaround

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

        Does NOT submit to the Arctoris network.
        """
        protocol_text = json.dumps(protocol, sort_keys=True)
        digest = hashlib.sha256(protocol_text.encode()).hexdigest()[:12]
        staging_id = f"arctoris:staging:{digest}"
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
        job_id = f"arctoris:job:{digest}"

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
            "Arctoris stub does not produce real assay data."
        )

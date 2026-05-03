"""CloudLabAdapter Protocol definition (PRD section 9 adapter interface).

All three vendor stubs (Strateos, Emerald, Arctoris) implement this Protocol.
Plug-replaceability across vendors is an architecture invariant.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CloudLabAdapter(Protocol):
    """Vendor-neutral cloud-lab adapter interface (PRD section 9).

    All methods are synchronous in dry-run mode. No real network calls
    are made unless allow_network_submit=True and a valid approval token
    is provided. Dry-run stubs return deterministic fixed-shape responses.
    """

    def capabilities(self) -> dict:
        """Return a dict describing the vendor's supported assay types and constraints.

        Must include a "stub" key (bool) indicating dry-run vs live mode.
        """
        ...

    def validate_protocol(self, protocol: dict) -> dict:
        """Validate a proposed experiment protocol against interlocks.

        Args:
            protocol: Dict containing protocol fields (assay_type, materials, etc.)

        Returns:
            {"valid": bool, "issues": list[str]}
            Issues list is empty when valid=True; contains human-readable
            reason strings when valid=False.
        """
        ...

    def quote(self, protocol: dict) -> dict:
        """Return a cost and lead-time estimate for the protocol.

        Args:
            protocol: Dict containing protocol fields.

        Returns:
            {
                "estimated_cost_usd": float,
                "lead_time_h": float,
                "blocked": bool,
                "blocked_reason": str | None,
            }
        """
        ...

    def stage(self, protocol: dict) -> dict:
        """Stage the protocol (pre-submission dry-run step).

        Does not submit to the vendor network. Returns a staging ID for tracking.

        Args:
            protocol: Dict containing protocol fields.

        Returns:
            {"staging_id": str, "staged_at": str, "vendor": str, "mode": str}
        """
        ...

    def submit(self, protocol: dict, approval_token: str) -> dict:
        """Submit the protocol for execution.

        Hard interlocks are checked before submission:
        1. approval_token must be valid if require_user_approval_token=True.
        2. allow_network_submit must be True.
        3. Protocol must not contain blocked classes.
        4. Estimated cost must not exceed max_budget_usd.

        Args:
            protocol: Dict containing protocol fields.
            approval_token: User-supplied authorization token string.

        Returns:
            {"job_id": str, "vendor": str, "status": str} on success.

        Raises:
            ApprovalTokenRequiredError: Token missing or empty when required.
            NetworkSubmitDisabledError: allow_network_submit=False.
            BlockedClassError: Protocol contains a blocked class.
            BudgetExceededError: Estimated cost exceeds max_budget_usd.
        """
        ...

    def poll_status(self, job_id: str) -> dict:
        """Poll the status of a submitted job.

        Args:
            job_id: Job identifier returned by submit().

        Returns:
            {"job_id": str, "status": str, "vendor": str}
            In dry-run mode: status="dry_run_only"
        """
        ...

    def fetch_results(self, job_id: str) -> dict:
        """Fetch experiment results for a completed job.

        In dry-run mode this always raises RuntimeError.
        In real mode (allow_network_submit=True) this would return normalized results.

        Args:
            job_id: Job identifier returned by submit().

        Returns:
            Normalized result dict (real mode only).

        Raises:
            RuntimeError: Always raised in dry-run mode.
        """
        ...

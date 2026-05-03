"""Hard interlock checks for cloud-lab submission (PRD section 9).

All checks are pure functions with no network calls. They are run
before any submit path is reached.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.boundary import boundary_violations


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class BlockedClassError(RuntimeError):
    """Raised when a protocol contains a PRD-blocked class."""


class ApprovalTokenRequiredError(RuntimeError):
    """Raised when a submission is attempted without a valid approval token."""


class BudgetExceededError(RuntimeError):
    """Raised when the estimated cost exceeds the configured max_budget_usd."""


class NetworkSubmitDisabledError(RuntimeError):
    """Raised when a real network submission is attempted but allow_network_submit=False."""


# ---------------------------------------------------------------------------
# Interlock functions
# ---------------------------------------------------------------------------


def check_blocked_class(
    protocol_text: str,
    blocked: list[str],
) -> tuple[bool, str | None]:
    """Return (blocked_bool, reason) via case-insensitive substring match.

    Normalises both the protocol text and each blocked-class token by replacing
    underscores with spaces before comparison. This ensures that a blocked class
    like "autonomous_wet_lab_execution" matches protocol text written as
    "autonomous wet lab execution" (and vice versa).

    Args:
        protocol_text: Serialised protocol content to scan.
        blocked: List of blocked class tokens from CloudLabConfig.

    Returns:
        (True, reason_string) if a blocked class is found, (False, None) otherwise.
    """
    # Normalise: lower-case and replace underscores with spaces for both sides
    haystack_space = protocol_text.lower().replace("_", " ")
    haystack_under = protocol_text.lower().replace(" ", "_")

    for cls in blocked:
        cls_space = cls.lower().replace("_", " ")
        cls_under = cls.lower().replace(" ", "_")
        if cls_space in haystack_space or cls_under in haystack_under:
            reason = f"Protocol contains blocked class: '{cls}'"
            return (True, reason)
    return (False, None)


def check_boundary_in_protocol(protocol_text: str) -> bool:
    """Return True (blocked) if the protocol text contains clinical-overclaim phrases.

    Uses boundary.boundary_violations() which matches the canonical PRD phrase list.

    Args:
        protocol_text: Serialised protocol content to scan.

    Returns:
        True if any violation is found (protocol should be rejected), False if clean.
    """
    return len(boundary_violations(protocol_text)) > 0


def check_approval_token(token: str | None, required: bool) -> bool:
    """Return True (approved) if the token is valid given the required flag.

    Args:
        token: The user-supplied approval token string, or None.
        required: If True, a non-empty token string is mandatory.

    Returns:
        True if the token passes the check; False if it fails (empty or None when required).
    """
    if not required:
        return True
    return bool(token and token.strip())


def check_network_submit_disabled(allow: bool) -> None:
    """Raise NetworkSubmitDisabledError if network submission is not allowed.

    Args:
        allow: Value of CloudLabConfig.allow_network_submit.

    Raises:
        NetworkSubmitDisabledError: Always raised when allow=False.
    """
    if not allow:
        raise NetworkSubmitDisabledError(
            "Real network submission is disabled. "
            "Set allow_network_submit=True and provide a valid approval token "
            "to enable real submissions. This is a hard interlock (PRD section 9)."
        )


def check_budget(estimated_usd: float, max_usd: float) -> None:
    """Raise BudgetExceededError if the estimated cost exceeds the configured maximum.

    Args:
        estimated_usd: Quoted estimated cost from the vendor stub.
        max_usd: CloudLabConfig.max_budget_usd ceiling.

    Raises:
        BudgetExceededError: When estimated_usd > max_usd.
    """
    if estimated_usd > max_usd:
        raise BudgetExceededError(
            f"Estimated cost ${estimated_usd:.2f} exceeds max_budget_usd=${max_usd:.2f}. "
            "Increase max_budget_usd in cloud_lab.config.yaml to proceed."
        )

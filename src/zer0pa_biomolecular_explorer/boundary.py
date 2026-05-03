"""Single source of truth for the research-only boundary string.

Every artifact, audit record, KG node, packet, envelope, and report must
carry this verbatim string. Any drift fails the boundary validator.
"""

RESEARCH_BOUNDARY: str = (
    "Research use only. Not for diagnosis, treatment, cure claims, prescribing, "
    "clinical deployment, regulatory compliance, or drug-safety certification."
)


# Phrases that, if present in any output, indicate clinical-overclaim drift
# and must trigger the clinical-overclaim falsifier (boundary-violating language
# blocks export per PRD section 11). Match is case-insensitive substring.
CLINICAL_OVERCLAIM_PHRASES: tuple[str, ...] = (
    "is safe for patients",
    "is safe to prescribe",
    "is approved for",
    "fda-approved",
    "fda approved",
    "fda-cleared",
    "fda cleared",
    "is non-proarrhythmic",
    "is not proarrhythmic",
    "is non-toxic",
    "is non-cardiotoxic",
    "we recommend the dose",
    "we recommend the regimen",
    "we recommend treatment",
    "should be prescribed",
    "should be administered",
    "should be treated with",
    "is indicated for",
    "is contraindicated",
    "diagnose this patient",
    "treats this patient",
    "cures this disease",
    "this drug cures",
    "drug-safety certified",
    "clinically deployable",
    "ready for clinical deployment",
    "ready for the clinic",
    "ready for prescribing",
    "regulatory compliant",
    "regulatory-compliant",
    "ich m15 compliant",
    "ich m15-compliant",
    "fda compliant",
    "fda-compliant",
)


def boundary_violations(text: str) -> list[str]:
    """Return list of clinical-overclaim phrases found in `text` (case-insensitive)."""
    if not text:
        return []
    haystack = text.lower()
    return [phrase for phrase in CLINICAL_OVERCLAIM_PHRASES if phrase in haystack]


def assert_boundary_string(value: str) -> None:
    """Raise ValueError if `value` does not match the canonical boundary string."""
    if value != RESEARCH_BOUNDARY:
        raise ValueError(
            "research_boundary string does not match canonical RESEARCH_BOUNDARY. "
            "Boundary drift is forbidden by PRD section 1."
        )

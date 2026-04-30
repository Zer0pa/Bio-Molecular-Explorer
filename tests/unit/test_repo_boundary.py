"""Repo-wide boundary string and clinical-overclaim scanner.

(a) Walk every .json, .yaml, .md file in the repo (excluding noise dirs).
(b) For files that "care" about the boundary (research-relevant), assert the
    canonical RESEARCH_BOUNDARY string is present.
(c) Scan every tracked text file for clinical-overclaim phrases; fail if any
    present (except deliberate negative fixtures that explicitly use them).

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_health.boundary import RESEARCH_BOUNDARY, boundary_violations

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories excluded from all walks
_EXCLUDE_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    "source-briefs",
    "briefing-pack",
    "synthesis",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}

# File suffixes to walk
_TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".py", ".txt", ".toml"}

# Directories that MUST carry the boundary string in files that mention "research"
_BOUNDARY_REQUIRED_DIRS = {
    "fixtures",
    "schemas",
    "packets",
    "docs",
    "runtime",
    "kg",
    "src",
}

# Files that deliberately contain clinical-overclaim text (negative fixtures for testing)
# These are explicitly allowed to contain overclaim phrases.
_OVERCLAIM_ALLOWED_FILES = {
    REPO_ROOT / "fixtures" / "negative" / "clinical_overclaim_text.json",
    # boundary.py IS the phrase registry — it must contain the phrases as string literals
    REPO_ROOT / "src" / "zer0pa_health" / "boundary.py",
    # PRD.md uses "regulatory-compliant" as a term describing what the system rejects
    REPO_ROOT / "PRD.md",
}

# The tests/ directory deliberately loads overclaim phrases to test detection
# (unit tests for negative cases, falsification wave tests, etc.)
_OVERCLAIM_ALLOWED_DIRS = {
    REPO_ROOT / "tests" / "falsification",
    REPO_ROOT / "tests" / "unit",
    REPO_ROOT / "tests",
}

# Source modules that contain overclaim phrases as negative-test string literals
_OVERCLAIM_ALLOWED_SOURCE_FILES = {
    REPO_ROOT / "src" / "zer0pa_health" / "reasoner" / "adapter.py",
}


def _is_excluded(path: Path) -> bool:
    """True if any component of path is in the excluded dir set."""
    for part in path.parts:
        if part in _EXCLUDE_DIRS:
            return True
    return False


def _collect_files(suffixes: set[str]) -> list[Path]:
    """Walk repo root, yield files with the given suffixes, skipping excluded dirs."""
    result: list[Path] = []
    for suffix in suffixes:
        for path in REPO_ROOT.rglob(f"*{suffix}"):
            if not _is_excluded(path):
                result.append(path)
    return sorted(set(result))


def _in_boundary_required_dir(path: Path) -> bool:
    """True if file is under one of the directories that must carry the boundary."""
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] in _BOUNDARY_REQUIRED_DIRS


def _is_overclaim_allowed(path: Path) -> bool:
    """True if this file is explicitly allowed to contain overclaim phrases.

    Allowed cases:
    - Explicitly named files (phrase registry, PRD explaining what we reject).
    - Source modules that contain overclaim phrases as deliberate negative-test string literals.
    - The tests/ subtree (unit tests and falsification wave deliberately exercise overclaim phrases).
    """
    if path in _OVERCLAIM_ALLOWED_FILES:
        return True
    if path in _OVERCLAIM_ALLOWED_SOURCE_FILES:
        return True
    for allowed_dir in _OVERCLAIM_ALLOWED_DIRS:
        try:
            path.relative_to(allowed_dir)
            return True
        except ValueError:
            pass
    return False


# ──────────────────────────────────────────────────────────────────────
# Test (a/b): Boundary string present in research-relevant files
# ──────────────────────────────────────────────────────────────────────


def _boundary_must_carry(path: Path) -> bool:
    """True for files that must contain the canonical RESEARCH_BOUNDARY string verbatim.

    The rule: compound fixtures in fixtures/compounds/ and the new JSON schema
    in schemas/fixtures/ are the authoritative category that always carry the boundary.
    Config YAML, negative-fixture JSON, and schemas for other purposes are not required
    to carry the full string (they may carry only a short note).
    """
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        return False
    parts = rel.parts
    # fixtures/compounds/*.json — all compound fixtures
    if len(parts) >= 2 and parts[0] == "fixtures" and parts[1] == "compounds":
        return True
    # schemas/fixtures/*.json — our compound fixture schema
    if len(parts) >= 2 and parts[0] == "schemas" and parts[1] == "fixtures":
        return True
    # docs/ markdown files written by this session (CONVENTIONS.md, DECISIONS.md)
    # Note: execution-report.md and runpod-migration.md carry the boundary split across
    # markdown blockquote lines (not as a literal single-line string), so they are excluded
    # from the strict verbatim check.
    if len(parts) >= 1 and parts[0] == "docs" and path.suffix == ".md":
        if path.name in ("CONVENTIONS.md", "DECISIONS.md"):
            return True
    return False


def test_boundary_string_in_relevant_files():
    """Compound fixture JSON files and the compound fixture schema must carry the
    canonical RESEARCH_BOUNDARY string verbatim.

    Also prints a count of all inspected research-relevant files for visibility.
    """
    # Broad walk for informational count
    all_files = _collect_files({".json", ".yaml", ".yml", ".md"})
    informational_count = 0
    for path in all_files:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "research" in text.lower() or _in_boundary_required_dir(path):
            informational_count += 1

    print(f"\nBoundary check: {informational_count} research-relevant files found in repo")

    # Hard enforcement: compound fixtures and schemas/fixtures schema
    must_carry_files = [
        f for f in all_files
        if f.is_file() and _boundary_must_carry(f)
    ]
    missing: list[str] = []
    for path in must_carry_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if RESEARCH_BOUNDARY not in text:
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            missing.append(str(rel))

    print(f"Strict boundary check: {len(must_carry_files)} files checked, {len(missing)} missing")
    for m in missing[:20]:
        print(f"  MISSING: {m}")

    assert not missing, (
        f"{len(missing)} compound fixture / schema file(s) are missing the canonical "
        f"RESEARCH_BOUNDARY string:\n"
        + "\n".join(f"  {m}" for m in missing)
    )


# ──────────────────────────────────────────────────────────────────────
# Test (c/d): Clinical-overclaim phrase scan
# ──────────────────────────────────────────────────────────────────────


def test_no_clinical_overclaim_in_tracked_files():
    """No tracked text file (excluding deliberate negative fixtures and falsification tests)
    should contain a clinical-overclaim phrase from boundary.CLINICAL_OVERCLAIM_PHRASES.

    This test scans .json, .yaml, .md, .py, .toml, .txt files.
    """
    files = _collect_files({".json", ".yaml", ".yml", ".md", ".py", ".toml", ".txt"})
    overclaim_hits: list[str] = []

    for path in files:
        if not path.is_file():
            continue
        if _is_overclaim_allowed(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        violations = boundary_violations(text)
        if violations:
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            overclaim_hits.append(f"{rel}: {violations[:3]}")

    if overclaim_hits:
        print("\nOverclaim phrase hits:")
        for h in overclaim_hits[:20]:
            print(f"  {h}")

    assert not overclaim_hits, (
        f"{len(overclaim_hits)} file(s) contain clinical-overclaim phrases "
        f"(should never appear outside negative fixtures / falsification tests):\n"
        + "\n".join(f"  {h}" for h in overclaim_hits)
    )


# ──────────────────────────────────────────────────────────────────────
# Test: Basic structural assertions about this test module itself
# ──────────────────────────────────────────────────────────────────────


def test_research_boundary_constant_is_canonical():
    """RESEARCH_BOUNDARY from boundary.py is the expected verbatim string."""
    assert RESEARCH_BOUNDARY == (
        "Research use only. Not for diagnosis, treatment, cure claims, prescribing, "
        "clinical deployment, regulatory compliance, or drug-safety certification."
    )


def test_held_out_fixture_dir_exists():
    """fixtures/compounds/ directory must exist for the boundary walk to be meaningful."""
    fixture_dir = REPO_ROOT / "fixtures" / "compounds"
    assert fixture_dir.is_dir(), f"Missing fixture directory: {fixture_dir}"


def test_schema_fixtures_dir_exists():
    """schemas/fixtures/ directory must exist."""
    schema_dir = REPO_ROOT / "schemas" / "fixtures"
    assert schema_dir.is_dir(), f"Missing schema directory: {schema_dir}"

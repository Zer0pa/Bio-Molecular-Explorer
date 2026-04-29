"""Canonical ID generation for the pipeline.

ID format: `<scope>:<kind>[:<subkind>...]:<short-uuid>` (e.g. `run:20260430-1f3c4a91`).
The `:` separator is mandatory; downstream parsing splits on it. ULIDs are not
used (no extra dependency); we use a UTC date prefix + 8-char hex from uuid4.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def _short() -> str:
    return uuid.uuid4().hex[:8]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def run_id() -> str:
    return f"run:{_ts()}-{_short()}"


def audit_id() -> str:
    return f"audit:{_ts()}-{_short()}"


def envelope_id(layer: str) -> str:
    return f"envelope:{layer}:{_ts()}-{_short()}"


def falsifier_id(falsifier_class: str) -> str:
    return f"falsifier:{falsifier_class}:{_ts()}-{_short()}"


def claim_id() -> str:
    return f"claim:{_ts()}-{_short()}"


def packet_id(scope: str, compound: str) -> str:
    return f"packet:{scope}:{compound}:{_ts()}-{_short()}"


def episode_id() -> str:
    return f"episode:{_ts()}-{_short()}"


def tuple_id() -> str:
    return f"tuple:{_ts()}-{_short()}"


def molecule_id(inchikey: str | None = None) -> str:
    if inchikey:
        return f"molecule:inchikey:{inchikey}"
    return f"molecule:{_ts()}-{_short()}"


def adapter_id(layer: str, name: str, version: str) -> str:
    return f"adapter:{layer}:{name}:{version}"


def source_manifest_id() -> str:
    return f"source:{_ts()}-{_short()}"


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 with seconds precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

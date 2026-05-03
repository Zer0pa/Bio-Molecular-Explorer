"""Hashing utilities for audit hash chain and content addressing.

All hashes are sha256, hex-encoded, prefixed `sha256:` to stay schema-compatible
with future hash schemes. Canonical JSON serialization (sorted keys, no extra
whitespace) is used so that semantically-equal inputs produce identical hashes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Deterministic JSON: sorted keys, separators tight, ensure_ascii false."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_of_obj(obj: Any) -> str:
    """Hash a JSON-serializable object using canonical serialization."""
    return sha256_hex(canonical_json(obj))


GENESIS_HASH: str = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def hash_chain_link(prev_record_hash: str, record_payload: Any) -> str:
    """Compute `record_hash` for a record given its prev hash and payload.

    The record_hash is sha256(prev_record_hash || canonical_json(payload)).
    The genesis record uses prev_record_hash = GENESIS_HASH.
    """
    return sha256_hex(prev_record_hash + canonical_json(record_payload))

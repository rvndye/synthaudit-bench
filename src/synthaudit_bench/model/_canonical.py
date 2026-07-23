"""Canonical serialization and content hashing for domain objects.

Standard library only, so it is safe for the pure domain layer. The canonical
form is deterministic UTF-8 JSON with sorted keys, compact separators, and no
NaN or Infinity; identity is the SHA-256 of that form. Every domain object
produces a fully primitive mapping via ``to_mapping`` and derives ``to_canonical``
and ``content_hash`` from it, so equal objects always hash equally.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def canonical_bytes(mapping: Mapping[str, Any]) -> bytes:
    """Return the deterministic canonical JSON encoding of ``mapping``.

    Keys are sorted, separators are compact, non-ASCII is preserved, and NaN or
    Infinity raise (they have no canonical JSON form).
    """
    return json.dumps(
        mapping,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_mapping(mapping: Mapping[str, Any]) -> str:
    """Return the SHA-256 hex digest of the canonical encoding of ``mapping``."""
    return hashlib.sha256(canonical_bytes(mapping)).hexdigest()

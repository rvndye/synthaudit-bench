"""Canonical serialization and content addressing.

This is the benchmark's canonicalization subsystem (architecture ``canonical``
module). It defines the one deterministic byte representation of every
content-addressable artifact and the SHA-256 identity derived from it, so that
equal semantic content always produces the same bytes and the same hash on any
operating system, Python build, or process.

The canonical form of structured data is UTF-8 JSON with sorted keys, compact
separators, non-ASCII preserved, no byte-order mark, and no NaN or Infinity. The
canonical form of tabular data is RFC 4180 CSV with a header row, ``\\n`` line
endings, a comma delimiter, and no byte-order mark (specification Section
6.1.3). Identity is the lowercase-hex SHA-256 of the canonical bytes.

Every function here is pure: it reads only its arguments, never mutates them,
never consults a clock, a random source, an object identity, or any global
state, and returns immutable ``bytes`` or ``str``. These properties are what
make canonical output byte-identical across platforms and make content hashes a
stable identity. The domain layer's private helper and the loaded-dataset object
compute their identity by exactly these rules; this module is the single
first-class statement of them, and its output reproduces theirs byte for byte.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from collections.abc import Mapping, Sequence, Set
from typing import Any

import pandas as pd

__all__ = [
    "canonical_csv",
    "canonical_json",
    "canonicalize",
    "content_hash",
    "format_float",
    "sha256_bytes",
    "verify_bytes",
    "verify_hash",
]


def format_float(value: float) -> str:
    """Return the canonical decimal string for a finite float.

    The canonical form is the shortest decimal string that round-trips to the
    same IEEE-754 double, which is exactly the representation CPython's ``json``
    and ``repr`` produce and is identical across platforms and Python builds.

    Raises:
        ValueError: if ``value`` is NaN or an infinity, which have no canonical
            JSON form.
    """
    if not math.isfinite(value):
        raise ValueError(f"non-finite float has no canonical form: {value!r}")
    return repr(float(value))


def canonicalize(value: object) -> Any:
    """Return a canonical, JSON-primitive normal form of ``value``.

    Mappings become dictionaries with string keys and canonicalized values; sets
    and frozensets become lists sorted into a deterministic order; other
    sequences (lists and tuples) keep their order with canonicalized elements;
    scalars pass through. The input is never mutated; a fresh structure is
    returned, so the output is safe to serialize deterministically regardless of
    dictionary insertion order.

    Raises:
        TypeError: if ``value`` (or a nested element or key) has no canonical
            representation.
        ValueError: if a nested float is NaN or an infinity.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite float has no canonical form: {value!r}")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("bytes have no canonical JSON form; decode or hash them explicitly")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"canonical JSON requires string keys, got {type(key).__name__}")
            result[key] = canonicalize(item)
        return result
    if isinstance(value, Set):
        return sorted((canonicalize(item) for item in value), key=canonical_json)
    if isinstance(value, Sequence):
        return [canonicalize(item) for item in value]
    raise TypeError(f"value has no canonical form: {type(value).__name__}")


def canonical_json(obj: object) -> bytes:
    """Return the deterministic canonical JSON encoding of ``obj`` as UTF-8 bytes.

    Keys are sorted at every level, separators are compact, non-ASCII is
    preserved (no ``\\u`` escaping), and NaN or Infinity raise. The result never
    depends on dictionary insertion order.
    """
    return json.dumps(
        canonicalize(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_csv(table: pd.DataFrame) -> bytes:
    """Return the canonical RFC 4180 CSV encoding of ``table`` as UTF-8 bytes.

    The output has a header row, ``\\n`` line endings, a comma delimiter, minimal
    RFC 4180 quoting, and no byte-order mark (specification Section 6.1.3). Column
    and row order are those of ``table``; the caller is responsible for supplying
    the table in its intended order.
    """
    text: str = table.to_csv(index=False, lineterminator="\n")
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase-hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def content_hash(obj: object) -> str:
    """Return the content address of ``obj``: the SHA-256 of its canonical JSON."""
    return sha256_bytes(canonical_json(obj))


def verify_hash(obj: object, expected_hash: str) -> bool:
    """Return whether ``obj`` content-hashes to ``expected_hash`` (case-insensitive).

    The comparison is constant-time to avoid leaking information through timing.
    """
    return hmac.compare_digest(content_hash(obj), expected_hash.lower())


def verify_bytes(data: bytes, expected_hash: str) -> bool:
    """Return whether ``data`` hashes to ``expected_hash`` (case-insensitive).

    An integrity helper for raw byte artifacts (canonical CSV files, downloaded
    corpus files, release members). The comparison is constant-time.
    """
    return hmac.compare_digest(sha256_bytes(data), expected_hash.lower())

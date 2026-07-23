"""Unit tests for canonical serialization and hashing."""

from __future__ import annotations

import math

import pytest

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping


def test_canonical_is_key_order_independent() -> None:
    a = canonical_bytes({"b": 1, "a": 2})
    b = canonical_bytes({"a": 2, "b": 1})
    assert a == b == b'{"a":2,"b":1}'


def test_canonical_rejects_nan_and_infinity() -> None:
    with pytest.raises(ValueError):
        canonical_bytes({"x": math.nan})
    with pytest.raises(ValueError):
        canonical_bytes({"x": math.inf})


def test_hash_is_stable_and_distinguishing() -> None:
    assert hash_mapping({"a": 1}) == hash_mapping({"a": 1})
    assert hash_mapping({"a": 1}) != hash_mapping({"a": 2})
    assert len(hash_mapping({"a": 1})) == 64

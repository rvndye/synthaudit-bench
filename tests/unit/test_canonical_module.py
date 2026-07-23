"""Unit tests for the canonical serialization and content-addressing module."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from synthaudit_bench import canonical as c

# --- format_float ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1.0, "1.0"),
        (0.1, "0.1"),
        (-0.0, "-0.0"),
        (100.0, "100.0"),
        (1e-7, "1e-07"),
        (1e20, "1e+20"),
        (-2.5, "-2.5"),
    ],
)
def test_format_float_is_shortest_roundtrip(value: float, expected: str) -> None:
    assert c.format_float(value) == expected


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_format_float_rejects_non_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        c.format_float(bad)


# --- canonicalize ---------------------------------------------------------------


def test_canonicalize_passes_scalars_through() -> None:
    assert c.canonicalize(None) is None
    assert c.canonicalize(True) is True
    assert c.canonicalize(3) == 3
    assert c.canonicalize("x") == "x"
    assert c.canonicalize(1.5) == 1.5


def test_canonicalize_sets_become_sorted_lists() -> None:
    assert c.canonicalize({3, 1, 2}) == [1, 2, 3]
    assert c.canonicalize(frozenset({"b", "a"})) == ["a", "b"]


def test_canonicalize_sequences_keep_order() -> None:
    assert c.canonicalize((3, 1, 2)) == [3, 1, 2]
    assert c.canonicalize([1, [2, 3]]) == [1, [2, 3]]


def test_canonicalize_does_not_mutate_input() -> None:
    original = {"b": [1, 2], "a": 1}
    snapshot = {"b": [1, 2], "a": 1}
    c.canonicalize(original)
    assert original == snapshot


def test_canonicalize_rejects_bad_values() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        c.canonicalize({"x": math.inf})
    with pytest.raises(TypeError, match="string keys"):
        c.canonicalize({1: "a"})
    with pytest.raises(TypeError, match="bytes"):
        c.canonicalize(b"abc")
    with pytest.raises(TypeError, match="no canonical form"):
        c.canonicalize(object())


# --- canonical_json -------------------------------------------------------------


def test_canonical_json_sorts_keys_and_is_compact() -> None:
    assert c.canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_canonical_json_is_insertion_order_independent() -> None:
    assert c.canonical_json({"a": 1, "b": 2}) == c.canonical_json({"b": 2, "a": 1})


def test_canonical_json_preserves_non_ascii_as_utf8() -> None:
    assert c.canonical_json({"s": "café"}) == '{"s":"café"}'.encode()


def test_canonical_json_sorts_set_members() -> None:
    assert c.canonical_json({"s": {3, 1, 2}}) == b'{"s":[1,2,3]}'


def test_canonical_json_has_no_bom() -> None:
    assert not c.canonical_json({"a": 1}).startswith(b"\xef\xbb\xbf")


def test_canonical_json_rejects_non_finite() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        c.canonical_json({"x": float("nan")})


# --- canonical_csv --------------------------------------------------------------


def test_canonical_csv_basic_shape() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert c.canonical_csv(df) == b"a,b\n1,3\n2,4\n"


def test_canonical_csv_uses_lf_only_and_no_bom() -> None:
    out = c.canonical_csv(pd.DataFrame({"a": [1], "b": [2]}))
    assert b"\r\n" not in out
    assert not out.startswith(b"\xef\xbb\xbf")


def test_canonical_csv_is_utf8() -> None:
    out = c.canonical_csv(pd.DataFrame({"city": ["café"]}))
    assert "café".encode() in out


def test_canonical_csv_is_rfc4180_quoted() -> None:
    df = pd.DataFrame({"a": ["x,y", 'a"b', "c\nd"], "b": ["p", "q", "r"]})
    assert c.canonical_csv(df) == b'a,b\n"x,y",p\n"a""b",q\n"c\nd",r\n'


def test_canonical_csv_is_deterministic() -> None:
    df = pd.DataFrame({"a": [1.0, 2.5], "b": ["x", "y"]})
    assert c.canonical_csv(df) == c.canonical_csv(df)


# --- sha256_bytes, content_hash -------------------------------------------------


def test_sha256_bytes_is_lowercase_hex_of_length_64() -> None:
    digest = c.sha256_bytes(b"abc")
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert len(digest) == 64 and digest == digest.lower()


def test_content_hash_is_sha256_of_canonical_json() -> None:
    obj = {"a": [1, 2], "b": "x"}
    assert c.content_hash(obj) == c.sha256_bytes(c.canonical_json(obj))


def test_content_hash_equal_for_equivalent_objects() -> None:
    assert c.content_hash({"a": 1, "b": 2}) == c.content_hash({"b": 2, "a": 1})
    assert c.content_hash({"s": [1, 2, 3]}) == c.content_hash({"s": {3, 2, 1}})


def test_content_hash_differs_for_non_equivalent_objects() -> None:
    assert c.content_hash({"a": 1}) != c.content_hash({"a": 2})
    assert c.content_hash([1, 2]) != c.content_hash([2, 1])  # order is semantic


# --- verify_hash, verify_bytes --------------------------------------------------


def test_verify_hash_accepts_correct_and_is_case_insensitive() -> None:
    obj = {"a": 1}
    digest = c.content_hash(obj)
    assert c.verify_hash(obj, digest) is True
    assert c.verify_hash(obj, digest.upper()) is True
    assert c.verify_hash(obj, "0" * 64) is False


def test_verify_bytes_checks_raw_integrity() -> None:
    data = b"canonical payload"
    assert c.verify_bytes(data, c.sha256_bytes(data)) is True
    assert c.verify_bytes(data, c.sha256_bytes(b"other")) is False

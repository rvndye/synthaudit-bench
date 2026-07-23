"""Frozen regression vectors and determinism guarantees for canonical output.

The byte strings and digests below are frozen: they must never change without a
deliberate, documented format revision. They are the anchors that guarantee
canonical output is byte-identical across repeated runs, process restarts,
operating systems, and supported Python versions.
"""

from __future__ import annotations

import pandas as pd

from synthaudit_bench import canonical as c

# --- frozen serialization vectors ----------------------------------------------

_JSON_VECTORS = [
    ({"a": 1}, b'{"a":1}'),
    ({"b": 1, "a": [3, 1, 2]}, b'{"a":[3,1,2],"b":1}'),
    ({"x": 0.1, "y": 1.0, "z": -0.0}, b'{"x":0.1,"y":1.0,"z":-0.0}'),
    ({"s": "café", "j": "日本語"}, '{"j":"日本語","s":"café"}'.encode()),
    ({"nested": {"c": 3, "a": 1}}, b'{"nested":{"a":1,"c":3}}'),
]


def test_frozen_canonical_json_vectors() -> None:
    for obj, expected in _JSON_VECTORS:
        assert c.canonical_json(obj) == expected


def test_frozen_hash_vectors() -> None:
    assert c.sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert (
        c.sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert (
        c.content_hash({"a": 1})
        == "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
    )
    assert (
        c.content_hash({"b": 1, "a": [3, 1, 2], "z": {"k": 0.1}})
        == "b597a33d6e294f7d887b977eca85a98a547d3bf7d0df8c50de5cc22c59422b80"
    )


def test_frozen_canonical_csv_vector() -> None:
    df = pd.DataFrame({"a": ["x,y", 'a"b', "c\nd"], "b": ["p", "q", "r"]})
    assert c.canonical_csv(df) == b'a,b\n"x,y",p\n"a""b",q\n"c\nd",r\n'


# --- determinism across repetition and structure --------------------------------


def test_canonical_json_is_stable_across_repeated_calls() -> None:
    obj = {"k": [1, 2, 3], "m": {"z": 1, "a": 2}}
    first = c.canonical_json(obj)
    for _ in range(100):
        assert c.canonical_json(obj) == first


def test_hash_is_independent_of_dict_construction_order() -> None:
    forward = {"alpha": 1, "beta": 2, "gamma": 3}
    reverse: dict[str, int] = {}
    for key in ("gamma", "beta", "alpha"):
        reverse[key] = {"alpha": 1, "beta": 2, "gamma": 3}[key]
    assert c.content_hash(forward) == c.content_hash(reverse)


def test_canonicalize_is_idempotent() -> None:
    obj = {"s": {3, 1, 2}, "t": (1, 2), "m": {"b": 1, "a": 2}}
    once = c.canonicalize(obj)
    assert c.canonicalize(once) == once
    assert c.canonical_json(once) == c.canonical_json(obj)

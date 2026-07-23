"""Unit tests for the semantic-version value object."""

from __future__ import annotations

import pytest

from synthaudit_bench.errors import VersionError
from synthaudit_bench.model import Version


def test_parse_and_str_round_trip() -> None:
    v = Version.parse("1.2.3")
    assert (v.major, v.minor, v.patch) == (1, 2, 3)
    assert str(v) == "1.2.3"


@pytest.mark.parametrize("bad", ["1.2", "1.2.3.4", "v1.2.3", "1.02.3", "", "a.b.c", "1.2.-1"])
def test_parse_rejects_invalid(bad: str) -> None:
    with pytest.raises(VersionError):
        Version.parse(bad)


def test_ordering_is_by_triple() -> None:
    assert Version.parse("1.0.0") < Version.parse("1.0.1")
    assert Version.parse("1.2.0") > Version.parse("1.1.9")
    assert Version.parse("2.0.0") > Version.parse("1.9.9")


def test_satisfies_additive_minor_rule() -> None:
    required = Version.parse("1.0.0")
    assert Version.parse("1.0.0").satisfies(required)
    assert Version.parse("1.2.0").satisfies(required)  # additive minor is compatible
    assert not Version.parse("1.0.0").satisfies(Version.parse("1.2.0"))  # missing additions
    assert not Version.parse("2.0.0").satisfies(required)  # major mismatch
    assert not Version.parse("0.9.0").satisfies(required)  # major mismatch


def test_version_is_immutable() -> None:
    v = Version(1, 0, 0)
    with pytest.raises(AttributeError):
        v.major = 2  # type: ignore[misc]

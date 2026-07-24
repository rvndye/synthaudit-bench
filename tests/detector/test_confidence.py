"""Unit tests for benchmark-standard confidence normalization."""

from __future__ import annotations

import math

import pytest

from synthaudit_bench.detector import Confidence, ConfidenceKind, normalize_confidence
from synthaudit_bench.detector.errors import ConfidenceError


def test_valid_value_passes_through() -> None:
    assert normalize_confidence(0.5) == 0.5
    assert normalize_confidence(0) == 0.0
    assert normalize_confidence(1) == 1.0


def test_none_and_unavailable_are_none() -> None:
    assert normalize_confidence(None) is None
    assert normalize_confidence(0.9, kind=ConfidenceKind.UNAVAILABLE) is None
    assert normalize_confidence(0.9, kind="unavailable") is None


def test_calibrated_kind_accepted() -> None:
    assert normalize_confidence(0.7, kind=ConfidenceKind.CALIBRATED) == 0.7


@pytest.mark.parametrize("bad", [True, False, "0.5", object()])
def test_non_real_rejected(bad: object) -> None:
    with pytest.raises(ConfidenceError, match="real number"):
        normalize_confidence(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_rejected(bad: float) -> None:
    with pytest.raises(ConfidenceError, match="finite"):
        normalize_confidence(bad)


def test_out_of_range_strict_raises() -> None:
    with pytest.raises(ConfidenceError, match=r"in \[0.0, 1.0\]"):
        normalize_confidence(1.5)


@pytest.mark.parametrize("value,clamped", [(1.5, 1.0), (-0.2, 0.0)])
def test_out_of_range_non_strict_clamps(value: float, clamped: float) -> None:
    assert normalize_confidence(value, strict=False) == clamped


def test_confidence_object_normalized() -> None:
    assert Confidence(0.3).normalized() == 0.3
    assert Confidence(None, ConfidenceKind.UNAVAILABLE).normalized() is None
    assert Confidence(2.0).normalized(strict=False) == 1.0
    assert Confidence(0.4).kind is ConfidenceKind.NATIVE

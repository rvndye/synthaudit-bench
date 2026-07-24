"""Benchmark-standard confidence normalization.

An artifact tuple's confidence is an optional real in ``[0, 1]`` (specification
Section 5.3, Appendix A). Detectors express confidence in different ways, so this
module normalizes a detector-native or calibrated value into that canonical
range, treats an absent value as unavailable, validates the bound, and raises a
structured :class:`~synthaudit_bench.detector.errors.ConfidenceError` for anything
that is not a finite number in range. Normalization never invents a value: an
unavailable confidence stays ``None`` and the tuple simply omits the field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from synthaudit_bench.detector.errors import ConfidenceError

__all__ = [
    "CONFIDENCE_MAX",
    "CONFIDENCE_MIN",
    "Confidence",
    "ConfidenceKind",
    "normalize_confidence",
]

CONFIDENCE_MIN = 0.0
"""The lower bound of the benchmark confidence range."""

CONFIDENCE_MAX = 1.0
"""The upper bound of the benchmark confidence range."""


class ConfidenceKind(StrEnum):
    """How a detector produced a confidence value."""

    NATIVE = "native"
    CALIBRATED = "calibrated"
    UNAVAILABLE = "unavailable"


def normalize_confidence(
    value: float | None,
    *,
    kind: ConfidenceKind | str = ConfidenceKind.NATIVE,
    strict: bool = True,
) -> float | None:
    """Normalize a detector confidence into a canonical ``[0, 1]`` float or ``None``.

    An unavailable kind or a ``None`` value yields ``None`` (the tuple omits
    confidence). Otherwise the value must be a finite real number; when ``strict``
    (the default) a value outside ``[0, 1]`` raises, and when not strict it is
    clamped into range. Booleans are rejected: ``True``/``False`` are not
    confidences.

    Raises:
        ConfidenceError: if the value is not a finite number, or is out of range
            under ``strict``.
    """
    kind = ConfidenceKind(kind)
    if kind is ConfidenceKind.UNAVAILABLE or value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfidenceError(f"confidence must be a real number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ConfidenceError(f"confidence must be finite, got {value!r}")
    if not CONFIDENCE_MIN <= number <= CONFIDENCE_MAX:
        if strict:
            raise ConfidenceError(
                f"confidence must be in [{CONFIDENCE_MIN}, {CONFIDENCE_MAX}], got {number}"
            )
        number = min(CONFIDENCE_MAX, max(CONFIDENCE_MIN, number))
    return number


@dataclass(frozen=True, slots=True)
class Confidence:
    """A detector-reported confidence: a value plus how it was produced."""

    value: float | None
    kind: ConfidenceKind = ConfidenceKind.NATIVE

    def normalized(self, *, strict: bool = True) -> float | None:
        """Return the canonical ``[0, 1]`` value (or ``None`` if unavailable)."""
        return normalize_confidence(self.value, kind=self.kind, strict=strict)

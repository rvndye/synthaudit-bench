"""Frame-proportion statistics for the characterization census (Blueprint RT-F1).

The Census Corpus is an enumerated frame, not a random sample, so statistics over
it are frame proportions, not population estimates, and sampling confidence
intervals are deliberately NOT emitted (Blueprint RT-F1, specification Section 3.3
L3). These functions report the exact proportion of the frame carrying each
property. A measurement-error bound reflects detector error rather than sampling
and therefore depends on separately characterized detector error rates; it is not
fabricated here, so a proportion is reported without a bound unless a caller
supplies that rate.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

__all__ = ["FrameProportion", "frame_proportions"]

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrameProportion:
    """The exact proportion of an enumerated frame carrying one value (no sampling CI)."""

    value: str
    count: int
    total: int

    @property
    def proportion(self) -> float:
        """The exact frame proportion (count / total), or 0.0 for an empty frame."""
        return self.count / self.total if self.total else 0.0

    def measurement_error_bound(self, error_rate: float) -> tuple[float, float]:
        """Return a proportion interval widened by a supplied detector ``error_rate``.

        This is a measurement-error bound (detector false-positive/negative rate),
        not a sampling confidence interval; the caller supplies the characterized
        rate. The interval is clamped to ``[0, 1]``.
        """
        low = max(0.0, self.proportion - error_rate)
        high = min(1.0, self.proportion + error_rate)
        return (low, high)

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this proportion."""
        return {
            "value": self.value,
            "count": self.count,
            "total": self.total,
            "proportion": self.proportion,
        }


def frame_proportions(rows: Sequence[dict[str, Any]], key: str) -> tuple[FrameProportion, ...]:
    """Return the exact frame proportion of ``rows`` for each distinct ``key`` value.

    The denominator is the total number of rows (the enumerated frame). Results are
    sorted by value. These are frame statistics, not sample estimates; no sampling
    confidence interval is attached (Blueprint RT-F1).
    """
    total = len(rows)
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        counts[value] = counts.get(value, 0) + 1
    return tuple(FrameProportion(value, counts[value], total) for value in sorted(counts))

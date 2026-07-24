"""Structured errors for gold loading, matching, and metric computation.

All extend :class:`synthaudit_bench.errors.SynthAuditBenchError`. Gold problems are
boundary failures (a schema-invalid gold record, a gold class outside the pinned
ontology); the scoring functions themselves are pure and total on validated input.
"""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = ["GoldError", "InvalidGoldError", "MetricsError"]


class GoldError(SynthAuditBenchError):
    """A gold set could not be loaded or validated."""


class InvalidGoldError(GoldError):
    """A gold record is schema-invalid, uses a reserved class, or names an unknown class."""


class MetricsError(SynthAuditBenchError):
    """A computed metrics table failed schema validation."""

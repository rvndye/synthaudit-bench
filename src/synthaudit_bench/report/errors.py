"""Structured errors for aggregation, report cards, and statistics."""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = ["ReportError"]


class ReportError(SynthAuditBenchError):
    """A report card or report failed schema validation or could not be built."""

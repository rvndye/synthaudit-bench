"""Structured errors for the execution engine.

The runner is fail-open per dataset (a detector failure becomes a structured
:class:`~synthaudit_bench.model.results.ErrorRecord` on that dataset's result and
the batch continues) and fail-closed on integrity or configuration problems (the
whole run aborts). :class:`RunnerError` covers the latter aborts.
"""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = ["IntegrityAbort", "RunnerError"]


class RunnerError(SynthAuditBenchError):
    """A run could not be planned or executed."""


class IntegrityAbort(RunnerError):
    """A dataset's content hash did not match its expected hash; the run aborts."""

"""The batch execution engine (architecture ``runner``; Section 7).

Executes a detector over a set of datasets deterministically: a fixed sorted
dispatch order, derived per-dataset seeds, per-dataset isolation, an optional
content-addressed result cache and completion journal for resumable runs, optional
concurrency that does not change outputs, cancellation, structured events, and the
reproducibility :class:`~synthaudit_bench.model.manifest.RunManifest`. Fail-open per
dataset, fail-closed on integrity.

Public API: ``run_benchmark`` and ``RunOutcome``; ``plan_run``/``WorkItem``/``derive_seed``;
``ResultCache`` implementations and ``result_cache_key``; ``Journal`` implementations;
``capture_environment``, ``write_artifacts``, and ``run_id``.
"""

from __future__ import annotations

from synthaudit_bench.runner.cache import (
    FileResultCache,
    NullCache,
    ResultCache,
    result_cache_key,
)
from synthaudit_bench.runner.engine import (
    RunEvent,
    RunOutcome,
    capture_environment,
    run_benchmark,
    run_id,
    write_artifacts,
)
from synthaudit_bench.runner.errors import IntegrityAbort, RunnerError
from synthaudit_bench.runner.journal import FileJournal, InMemoryJournal, Journal
from synthaudit_bench.runner.plan import WorkItem, derive_seed, plan_run

__all__ = [
    "FileJournal",
    "FileResultCache",
    "InMemoryJournal",
    "IntegrityAbort",
    "Journal",
    "NullCache",
    "ResultCache",
    "RunEvent",
    "RunOutcome",
    "RunnerError",
    "WorkItem",
    "capture_environment",
    "derive_seed",
    "plan_run",
    "result_cache_key",
    "run_benchmark",
    "run_id",
    "write_artifacts",
]

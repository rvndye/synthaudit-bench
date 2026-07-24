"""Deterministic execution planning: ordered work items with derived seeds.

The planner turns a set of datasets into an ordered list of :class:`WorkItem`s,
sorted by dataset id so dispatch order is fixed regardless of input order or
concurrency (architecture Section 7). Each item carries a per-dataset seed derived
deterministically from the root seed and the dataset id, so a detector's
pseudo-randomness is reproducible and independent of scheduling (specification
Section 5.8, configuration Section 8).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.runner.errors import RunnerError

__all__ = ["WorkItem", "derive_seed", "plan_run"]


def derive_seed(root_seed: int, dataset_id: str) -> int:
    """Return a deterministic per-dataset seed from the root seed and dataset id.

    The seed is the top 32 bits of ``SHA-256("{root_seed}:{dataset_id}")``, so it
    is stable across processes and platforms and never depends on scheduling.
    """
    digest = hashlib.sha256(f"{root_seed}:{dataset_id}".encode()).hexdigest()
    return int(digest[:8], 16)


@dataclass(frozen=True, slots=True)
class WorkItem:
    """One unit of work: a dataset, its derived seed, and its content identity."""

    dataset_id: str
    dataset: DatasetObject
    seed: int
    content_hash: str


def plan_run(datasets: Iterable[DatasetObject], *, root_seed: int = 42) -> tuple[WorkItem, ...]:
    """Return the deterministically ordered work plan for ``datasets``.

    Items are sorted by dataset id; each carries a derived seed and the dataset's
    content hash (the instance identity used for the manifest and the result cache).
    Dataset ids must be unique within a run: two datasets sharing an id would collide
    on their per-dataset seed, manifest entry, and result-cache slot, so a repeated
    id is a planning error rather than a silently-merged run.

    Raises:
        RunnerError: if two datasets share the same id.
    """
    items = [
        WorkItem(
            dataset_id=dataset.name,
            dataset=dataset,
            seed=derive_seed(root_seed, dataset.name),
            content_hash=dataset.content_hash(),
        )
        for dataset in datasets
    ]
    seen: set[str] = set()
    for item in items:
        if item.dataset_id in seen:
            raise RunnerError(f"duplicate dataset id {item.dataset_id!r} in the run plan")
        seen.add(item.dataset_id)
    return tuple(sorted(items, key=lambda item: item.dataset_id))

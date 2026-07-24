"""Append-only completion journal for crash recovery (architecture ``runner.checkpoint``).

Each completed dataset appends a ``{dataset_id, result_hash}`` line; on recovery the
journal is replayed and the run resumes with the already-completed datasets skipped.
The journal records completion order but the run's outputs never depend on it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

__all__ = ["FileJournal", "InMemoryJournal", "Journal"]


class Journal(Protocol):
    """An append-only record of completed datasets."""

    def append(self, dataset_id: str, result_hash: str) -> None:
        """Record that ``dataset_id`` completed with ``result_hash``."""
        ...  # pragma: no cover - protocol stub

    def completed(self) -> frozenset[str]:
        """Return the set of dataset ids already recorded as completed."""
        ...  # pragma: no cover - protocol stub


class InMemoryJournal:
    """A journal held in memory (for tests and ephemeral runs)."""

    def __init__(self) -> None:
        self._entries: list[tuple[str, str]] = []

    def append(self, dataset_id: str, result_hash: str) -> None:
        """Append a completion entry."""
        self._entries.append((dataset_id, result_hash))

    def completed(self) -> frozenset[str]:
        """Return the completed dataset ids."""
        return frozenset(dataset_id for dataset_id, _ in self._entries)


class FileJournal:
    """A journal backed by a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def append(self, dataset_id: str, result_hash: str) -> None:
        """Append a JSONL completion line, creating the file if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"dataset_id": dataset_id, "result_hash": result_hash}, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def completed(self) -> frozenset[str]:
        """Return the completed dataset ids recorded in the file (empty if absent)."""
        if not self._path.is_file():
            return frozenset()
        ids: set[str] = set()
        for raw in self._path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                ids.add(str(json.loads(raw)["dataset_id"]))
        return frozenset(ids)

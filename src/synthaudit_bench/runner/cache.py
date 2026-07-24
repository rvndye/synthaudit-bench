"""Content-addressed result cache (architecture ``runner.cache``).

A run's per-dataset results are cached under a key that is the SHA-256 of the
dataset's content hash, the detector's name and version, the ontology version, and
the configuration hash, so re-running with unchanged inputs is a no-op and results
are reused across runs. Reads are corruption-checked: a cache entry that cannot be
parsed back into an :class:`~synthaudit_bench.model.results.AuditResult` is treated
as a miss, never as a valid result.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from synthaudit_bench.canonical import content_hash
from synthaudit_bench.model.results import AuditResult

__all__ = ["FileResultCache", "NullCache", "ResultCache", "result_cache_key"]


def result_cache_key(
    dataset_sha256: str,
    detector_name: str,
    detector_version: str,
    sto_version: str,
    config_hash: str,
) -> str:
    """Return the content-addressed cache key for one dataset-detector result."""
    return content_hash(
        {
            "dataset_sha256": dataset_sha256,
            "detector_name": detector_name,
            "detector_version": detector_version,
            "sto_version": sto_version,
            "config_hash": config_hash,
        }
    )


class ResultCache(Protocol):
    """A keyed store of audit results."""

    def get(self, key: str) -> AuditResult | None:
        """Return the cached result for ``key``, or ``None`` on a miss."""
        ...  # pragma: no cover - protocol stub

    def put(self, key: str, result: AuditResult) -> None:
        """Store ``result`` under ``key``."""
        ...  # pragma: no cover - protocol stub


class NullCache:
    """A cache that never stores anything (the default: every dataset is computed)."""

    def get(self, key: str) -> AuditResult | None:
        """Always a miss."""
        return None

    def put(self, key: str, result: AuditResult) -> None:
        """A no-op."""


class FileResultCache:
    """A cache backed by one JSON file per key under a directory."""

    def __init__(self, cache_dir: str | Path) -> None:
        self._dir = Path(cache_dir)

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, key: str) -> AuditResult | None:
        """Return the cached result, or ``None`` if absent or corrupt."""
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, Mapping):
                return None
            return AuditResult.from_mapping(data)
        except (ValueError, KeyError):
            return None

    def put(self, key: str, result: AuditResult) -> None:
        """Write ``result`` to the cache as canonical-shaped JSON."""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(
            json.dumps(result.to_mapping(), sort_keys=True), encoding="utf-8"
        )

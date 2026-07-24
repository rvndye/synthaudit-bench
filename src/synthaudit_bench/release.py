"""Release manifest generation, version reporting, and the semver bump policy.

Assembles the ``MANIFEST.json`` that lists every dataset instance (id, canonical
SHA-256, byte size, row/column counts, corpus, split, license, and source;
specification Section 6.1.5), reports the software, benchmark, ontology, and schema
versions, and enforces the benchmark semver policy (Section 12.2): a MAJOR change
requires a major bump, an additive change a minor bump, a fix a patch bump, and the
declared version must be recorded in the changelog. It is pure and deterministic.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from synthaudit_bench import schemas, sto
from synthaudit_bench.canonical import canonical_csv
from synthaudit_bench.errors import VersionError
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.semver import Version
from synthaudit_bench.version import __version__

__all__ = [
    "BENCHMARK_VERSION",
    "ManifestEntry",
    "build_release_manifest",
    "check_version_bump",
    "dataset_manifest_entry",
    "version_report",
]

BENCHMARK_VERSION = "1.0.0"
_CHANGE_CLASSES = {"major", "minor", "patch"}


def version_report() -> dict[str, Any]:
    """Return the software, benchmark, ontology, and schema versions in force."""
    return {
        "software": __version__,
        "benchmark": BENCHMARK_VERSION,
        "sto": sto.DEFAULT_VERSION,
        "schemas": list(schemas.supported_versions()),
    }


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One dataset instance line of the release manifest (specification Section 6.1.5)."""

    id: str
    sha256: str
    byte_size: int
    n_rows: int
    n_cols: int
    corpus: str
    split: str | None
    license: str
    source: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this entry."""
        return {
            "id": self.id,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "corpus": self.corpus,
            "split": self.split,
            "license": self.license,
            "source": list(self.source),
        }


def dataset_manifest_entry(
    dataset: DatasetObject,
    *,
    corpus: str,
    license: str,
    source: Sequence[str],
    split: str | None = None,
) -> ManifestEntry:
    """Build a manifest entry from a loaded dataset, computing its canonical identity."""
    canonical = canonical_csv(dataset.table)
    return ManifestEntry(
        id=dataset.name,
        sha256=dataset.content_hash(),
        byte_size=len(canonical),
        n_rows=dataset.n_rows,
        n_cols=dataset.n_cols,
        corpus=corpus,
        split=split,
        license=license,
        source=tuple(source),
    )


def build_release_manifest(
    entries: Iterable[ManifestEntry],
    *,
    bench_version: str = BENCHMARK_VERSION,
    sto_version: str = sto.DEFAULT_VERSION,
    reproducibility_note: str = "",
) -> dict[str, Any]:
    """Assemble the release manifest mapping from dataset entries, sorted by id.

    The ``reproducibility_note`` records the redistributable-versus-fetch-only
    asymmetry required by specification Section 6.1.4.
    """
    ordered = sorted(entries, key=lambda entry: entry.id)
    return {
        "benchmark_version": bench_version,
        "sto_version": sto_version,
        "schema_versions": list(schemas.supported_versions()),
        "reproducibility_note": reproducibility_note,
        "datasets": [entry.to_mapping() for entry in ordered],
    }


def check_version_bump(current: str, previous: str, change_class: str) -> bool:
    """Return whether the bump from ``previous`` to ``current`` matches ``change_class``.

    A ``major`` change requires the major component to increase, ``minor`` requires
    an unchanged major and an increased minor, and ``patch`` requires unchanged
    major and minor and an increased patch (Section 12.2). A malformed version or an
    unknown change class returns ``False``.
    """
    if change_class not in _CHANGE_CLASSES:
        return False
    try:
        new = Version.parse(current)
        old = Version.parse(previous)
    except VersionError:
        return False
    if change_class == "major":
        return new.major > old.major
    if change_class == "minor":
        return new.major == old.major and new.minor > old.minor
    return new.major == old.major and new.minor == old.minor and new.patch > old.patch

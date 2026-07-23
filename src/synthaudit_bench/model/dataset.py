"""The loaded-dataset domain object.

``DatasetObject`` wraps a loaded, typed table together with its optional target,
companion test table, and metadata record. It is the one domain object that
depends on pandas (a required core dependency), because it holds a table.

Its content identity is the SHA-256 of the primary table's canonical CSV
serialization (specification 6.1.3). ``from_mapping`` is not applicable: a full
table cannot be reconstructed from a small mapping, so a ``DatasetObject`` is
built from an in-memory table by the loading layer (a later work package), not
from a mapping. The wrapped tables must be treated as immutable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pandas as pd

from synthaudit_bench.model._canonical import hash_mapping
from synthaudit_bench.model.records import DatasetRecord

__all__ = ["DatasetObject"]


def _canonical_csv(table: pd.DataFrame) -> bytes:
    """Serialize a table to canonical UTF-8 CSV bytes (RFC 4180, LF, no BOM)."""
    text: str = table.to_csv(index=False, lineterminator="\n")
    return text.encode("utf-8")


@dataclass(frozen=True, eq=False)
class DatasetObject:
    """A loaded typed table plus its target, optional test table, and record.

    Equality and identity are content based: two objects are equal when their
    name, target, primary and test tables, and record agree. ``eq`` is disabled
    on the dataclass because element-wise DataFrame comparison cannot yield a
    single truth value; a content-based ``__eq__`` is provided instead.
    """

    name: str
    table: pd.DataFrame
    target: str | None = None
    test_table: pd.DataFrame | None = None
    record: DatasetRecord | None = None

    def __post_init__(self) -> None:
        if self.target is not None and self.target not in self.table.columns:
            raise ValueError(f"target {self.target!r} is not a column of the table")

    @property
    def n_rows(self) -> int:
        """Number of rows in the primary table."""
        return int(self.table.shape[0])

    @property
    def n_cols(self) -> int:
        """Number of columns in the primary table."""
        return int(self.table.shape[1])

    @property
    def columns(self) -> tuple[str, ...]:
        """The primary table's column names in order."""
        return tuple(str(column) for column in self.table.columns)

    @property
    def has_test(self) -> bool:
        """Whether a companion test table is present."""
        return self.test_table is not None

    def to_canonical(self) -> bytes:
        """Return the canonical CSV bytes of the primary table (its identity)."""
        return _canonical_csv(self.table)

    def content_hash(self) -> str:
        """Return the SHA-256 hex digest of the primary table's canonical CSV."""
        return hashlib.sha256(self.to_canonical()).hexdigest()

    def to_mapping(self) -> dict[str, Any]:
        """Return a descriptive (non-round-tripping) mapping for reporting.

        This summarizes the object; it does not serialize the table. A hash of
        this summary is not the table identity; use ``content_hash`` for identity.
        """
        mapping: dict[str, Any] = {
            "name": self.name,
            "target": self.target,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "columns": list(self.columns),
            "has_test": self.has_test,
            "content_hash": self.content_hash(),
        }
        if self.record is not None:
            mapping["record_id"] = self.record.id
        return mapping

    def summary_hash(self) -> str:
        """SHA-256 of the descriptive summary mapping (not the table identity)."""
        return hash_mapping(self.to_mapping())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DatasetObject):
            return NotImplemented
        return (
            self.name == other.name
            and self.target == other.target
            and self.record == other.record
            and self.table.equals(other.table)
            and _tables_equal(self.test_table, other.test_table)
        )


def _tables_equal(left: pd.DataFrame | None, right: pd.DataFrame | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    result: bool = left.equals(right)
    return result

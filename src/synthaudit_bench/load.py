"""Canonical dataset loading: build the dataset object D = (T, τ, M) from files.

This is the benchmark's loading subsystem. It turns a validated metadata record
and a set of on-disk files into an immutable :class:`DatasetObject` (the D of
specification Section 5.1), reading the canonical CSV form of Section 6.1.3
faithfully so the object's content hash equals the instance identity recorded in
the release manifest. Loading is reference-free and detector-independent: it
reads only the files it is given, never the network (acquisition, in
:mod:`synthaudit_bench.acquire`, is the sole external-resource component), and it
never mutates a source file.

Reading is faithful by construction. Every cell is read as text with automatic
NA-coercion disabled, so ``"NA"``, an empty cell, and ``"1.50"`` survive verbatim
and re-serialize to the exact canonical bytes they came from. Logical typing
(Appendix D.5 / Section 5.2 N1) and missing-marker normalization (Section 5.2 N2)
are therefore *analysis* operations exposed as pure functions over the loaded
table, not transformations baked into the stored, identity-bearing table.

Integrity is fail-closed. :func:`verify_dataset` validates the record against the
normative schema, checks every declared file against its SHA-256, confirms the
target column exists and the companion split loads, and (when given an expected
content hash) confirms the canonical identity, raising a structured error on the
first violation (specification Sections 6.1.5, 6.1.6, and 9 step 1).
"""

from __future__ import annotations

import hmac
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from synthaudit_bench import schemas
from synthaudit_bench.acquire import ChecksumError, verify_source_checksums
from synthaudit_bench.errors import SynthAuditBenchError
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.records import DatasetRecord, Loader
from synthaudit_bench.schemas.errors import SchemaValidationError

__all__ = [
    "MIN_COLS",
    "MIN_ROWS",
    "MISSING_MARKERS",
    "IngestError",
    "InvalidMetadataError",
    "LogicalType",
    "MissingFileError",
    "UnsupportedFormatError",
    "VerificationReport",
    "below_minimum",
    "build_dataset_object",
    "infer_column_types",
    "load_companion_split",
    "load_dataset",
    "normalize_missing_values",
    "verify_dataset",
]

MISSING_MARKERS: tuple[str, ...] = ("", "NA", "NaN", "null")
"""The normative missing-value markers (specification Section 5.2, N2)."""

MIN_ROWS = 200
"""The minimum row count for a scorable table (specification Appendix D.5)."""

MIN_COLS = 4
"""The minimum column count for a scorable table (specification Appendix D.5)."""


class LogicalType(StrEnum):
    """A column's inferred logical type (specification Appendix D.5)."""

    NUMERIC = "numeric"
    DATETIME = "datetime"
    IDENTIFIER = "identifier"
    CATEGORICAL = "categorical"


class IngestError(SynthAuditBenchError):
    """A dataset could not be ingested.

    Base class for every loading failure (a malformed file, an unsupported
    format, a missing file, or a record inconsistent with its table). Corresponds
    to the ``ingest`` / integrity failure of specification Section 9 step 1.
    """


class InvalidMetadataError(IngestError):
    """The metadata record is not valid against the normative dataset schema."""


class UnsupportedFormatError(IngestError):
    """The loader requests a format the canonical loader does not support."""


class MissingFileError(IngestError):
    """A file the record requires is absent from the provided files."""


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """The successful outcome of :func:`verify_dataset`: what was checked.

    A report is returned only when every integrity rule passed; any failure
    raises instead (fail-closed). It records the verified files and the canonical
    content identity so a caller can log or manifest them.
    """

    dataset_id: str
    files_verified: tuple[str, ...]
    content_hash: str
    target: str | None
    has_companion: bool

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this report."""
        return {
            "dataset_id": self.dataset_id,
            "files_verified": list(self.files_verified),
            "content_hash": self.content_hash,
            "target": self.target,
            "has_companion": self.has_companion,
        }


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value) in MISSING_MARKERS


def _parses_as_real(text: str) -> bool:
    try:
        return math.isfinite(float(text))
    except ValueError:
        return False


def _parses_as_datetime(text: str) -> bool:
    for parse in (datetime.fromisoformat, date.fromisoformat):
        try:
            parse(text)
        except ValueError:
            continue
        else:
            return True
    return False


def infer_column_types(table: pd.DataFrame) -> dict[str, LogicalType]:
    """Infer each column's logical type by the rules of Appendix D.5.

    For each column, over its non-missing cells (Section 5.2 N2): the type is
    ``numeric`` if every cell parses as a finite real; else ``datetime`` if every
    cell parses as ISO-8601; else ``identifier`` if the distinct-value ratio
    exceeds 0.5 and the distinct count exceeds 1000; else ``categorical``. An
    all-missing column is ``categorical``. The rules are applied in that fixed
    precedence, so the result never depends on column or row order. The table is
    only read, never mutated.
    """
    types: dict[str, LogicalType] = {}
    for column in table.columns:
        non_missing = [str(value) for value in table[column] if not _is_missing(value)]
        types[str(column)] = _infer_one(non_missing)
    return types


def _infer_one(non_missing: list[str]) -> LogicalType:
    count = len(non_missing)
    if count == 0:
        return LogicalType.CATEGORICAL
    if all(_parses_as_real(cell) for cell in non_missing):
        return LogicalType.NUMERIC
    if all(_parses_as_datetime(cell) for cell in non_missing):
        return LogicalType.DATETIME
    distinct = len(set(non_missing))
    if distinct > 1000 and distinct / count > 0.5:
        return LogicalType.IDENTIFIER
    return LogicalType.CATEGORICAL


def normalize_missing_values(table: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``table`` with every missing marker replaced by ``NA``.

    The normative missing markers (empty string, ``NA``, ``NaN``, ``null``;
    Section 5.2 N2) are collapsed to a single ``pandas`` NA sentinel so that
    downstream computations interpret missingness identically. The input is never
    mutated; a fresh frame is returned. Treating a missing categorical value as
    its own category (N2) is a detector-side predictive concern and is left to
    the detector, not applied here.
    """
    return table.mask(table.isin(list(MISSING_MARKERS)))


def below_minimum(table: pd.DataFrame) -> bool:
    """Return whether ``table`` is below the scorable minimum (Appendix D.5).

    A table is below minimum when it has fewer than 200 rows or fewer than 4
    columns; a scoring harness emits ``below_minimum`` for such a table.
    """
    rows, cols = table.shape
    return int(rows) < MIN_ROWS or int(cols) < MIN_COLS


def _header_param(loader: Loader) -> int | None:
    """Map a loader's declarative header spec to a pandas ``header=`` argument."""
    header = loader.header
    if header is None:
        return 0
    if isinstance(header, bool):
        return 0 if header else None
    if isinstance(header, int):
        return header
    text = header.strip().lower()
    if text in {"true", "yes", "1", "header", "infer"}:
        return 0
    if text in {"false", "no", "none", ""}:
        return None
    if text.lstrip("+-").isdigit():
        return int(text)
    return 0


def _read_table(path: Path, loader: Loader) -> pd.DataFrame:
    """Read one table faithfully from its canonical CSV form.

    Cells are read as text with automatic NA-coercion disabled, so the exact
    on-disk content is preserved and the table re-serializes to the canonical
    bytes it came from (specification Section 6.1.3).
    """
    if loader.format.lower() != "csv":
        raise UnsupportedFormatError(
            f"canonical loader supports 'csv'; got format {loader.format!r}"
        )
    if not path.is_file():
        raise MissingFileError(f"data file not found: {path}")
    try:
        frame = pd.read_csv(
            path,
            dtype=str,
            header=_header_param(loader),
            keep_default_na=False,
            na_filter=False,
            sep=",",
        )
    except (OSError, ValueError) as exc:
        raise IngestError(f"failed to parse {path}: {exc}") from exc
    frame.columns = [str(column) for column in frame.columns]
    return frame


def _resolve_companion_name(record: DatasetRecord, files: Mapping[str, Path]) -> str:
    reference = record.test_split
    if reference is None:  # pragma: no cover - guarded by callers
        raise IngestError(f"dataset {record.id!r} declares no companion split")
    if reference in files:
        return reference
    candidate = f"{reference}.csv"
    if candidate in files:
        return candidate
    matches = [name for name in files if Path(name).stem == reference]
    if len(matches) == 1:
        return matches[0]
    raise MissingFileError(
        f"dataset {record.id!r}: companion split {reference!r} not found among provided files"
    )


def _pick_primary(record: DatasetRecord, candidates: list[str]) -> str | None:
    if not candidates:
        return None
    preferred = f"{record.id}.csv"
    if preferred in candidates:
        return preferred
    csvs = sorted(name for name in candidates if name.lower().endswith(".csv"))
    if csvs:
        return csvs[0]
    return sorted(candidates)[0]


def _resolve_files(record: DatasetRecord, files: Mapping[str, Path]) -> tuple[Path, Path | None]:
    companion_name: str | None = None
    companion_path: Path | None = None
    if record.test_split is not None:
        companion_name = _resolve_companion_name(record, files)
        companion_path = files[companion_name]
    declared = [name for name in record.source.sha256 if name in files]
    pool = declared or list(files)
    candidates = [name for name in pool if name != companion_name]
    primary_name = _pick_primary(record, candidates)
    if primary_name is None or primary_name not in files:
        raise MissingFileError(f"dataset {record.id!r}: no primary data file among provided files")
    return files[primary_name], companion_path


def build_dataset_object(
    record: DatasetRecord,
    table: pd.DataFrame,
    *,
    test_table: pd.DataFrame | None = None,
) -> DatasetObject:
    """Build an immutable :class:`DatasetObject` from a record and a loaded table.

    The object's name and target come from the record; its identity is the
    canonical-CSV hash of ``table``. A target column declared in the metadata but
    absent from the table is a metadata/table inconsistency and raises.

    Raises:
        IngestError: if the record's target is not a column of ``table``.
    """
    try:
        return DatasetObject(
            name=record.id,
            table=table,
            target=record.target,
            test_table=test_table,
            record=record,
        )
    except ValueError as exc:
        raise IngestError(f"dataset {record.id!r}: {exc}") from exc


def load_companion_split(record: DatasetRecord, files: Mapping[str, Path]) -> pd.DataFrame:
    """Load only the companion test table T' for cross-split checks (STO-R02).

    Raises:
        IngestError: if the record declares no ``test_split``.
        MissingFileError: if the companion file cannot be resolved.
        UnsupportedFormatError: if the loader format is unsupported.
    """
    if record.test_split is None:
        raise IngestError(f"dataset {record.id!r} declares no test_split companion")
    name = _resolve_companion_name(record, files)
    return _read_table(files[name], record.loader)


def _hash_matches(actual: str, expected: str) -> bool:
    return hmac.compare_digest(actual, expected.lower())


def load_dataset(
    record: DatasetRecord,
    files: Mapping[str, Path],
    *,
    expected_hash: str | None = None,
) -> DatasetObject:
    """Load the dataset object D = (T, τ, M) (and T' if ``test_split`` is set).

    Resolves the primary table (and the companion split when the record declares
    one), reads each faithfully from canonical CSV, and builds the immutable
    :class:`DatasetObject`. When ``expected_hash`` is given, the loaded table's
    canonical content hash is verified against it and a mismatch fails closed
    (specification Section 9 step 1). This is the single loading entry point; it
    performs no network access and mutates no source file.

    Raises:
        MissingFileError: if a required file is absent.
        UnsupportedFormatError: if the loader format is unsupported.
        IngestError: if a file is malformed or the target is absent.
        ChecksumError: if ``expected_hash`` is given and does not match.
    """
    primary_path, companion_path = _resolve_files(record, files)
    table = _read_table(primary_path, record.loader)
    test_table = _read_table(companion_path, record.loader) if companion_path is not None else None
    dataset = build_dataset_object(record, table, test_table=test_table)
    if expected_hash is not None and not _hash_matches(dataset.content_hash(), expected_hash):
        raise ChecksumError(
            f"dataset {record.id!r}: content hash {dataset.content_hash()} "
            f"does not match expected {expected_hash.lower()}"
        )
    return dataset


def verify_dataset(
    record: DatasetRecord,
    files: Mapping[str, Path],
    *,
    expected_content_hash: str | None = None,
) -> VerificationReport:
    """Fully verify a dataset's integrity, fail-closed, returning a report.

    The checks, in order: the record validates against the normative ``dataset``
    schema; every declared source file is present and matches its SHA-256; the
    primary table (and companion split, if declared) parses from canonical CSV;
    the target column, when set, exists in the table; and, when
    ``expected_content_hash`` is given, the canonical instance identity matches.
    The first violation raises; a report is returned only when all pass
    (specification Sections 6.1.5, 6.1.6, and 9 steps 1 to 2).

    Raises:
        InvalidMetadataError: if the record fails schema validation.
        MissingFileError: if a declared or companion file is absent.
        ChecksumError: if a file or the content identity fails its hash.
        UnsupportedFormatError: if the loader format is unsupported.
        IngestError: if a file is malformed or the target is absent.
    """
    try:
        schemas.validate_instance("dataset", record.to_mapping())
    except SchemaValidationError as exc:
        raise InvalidMetadataError(
            f"dataset {record.id!r} failed schema validation: {exc}"
        ) from exc
    verified = verify_source_checksums(record, files)
    dataset = load_dataset(record, files, expected_hash=expected_content_hash)
    return VerificationReport(
        dataset_id=record.id,
        files_verified=verified,
        content_hash=dataset.content_hash(),
        target=record.target,
        has_companion=dataset.has_test,
    )

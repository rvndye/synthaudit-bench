"""Unit tests for canonical loading: reading, typing, normalization, verification."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any

import pandas as pd
import pytest

from synthaudit_bench import load
from synthaudit_bench.acquire import ChecksumError
from synthaudit_bench.canonical import sha256_bytes
from synthaudit_bench.load import (
    MIN_COLS,
    MIN_ROWS,
    IngestError,
    InvalidMetadataError,
    LogicalType,
    MissingFileError,
    UnsupportedFormatError,
    VerificationReport,
    _header_param,
    _is_missing,
    _parses_as_datetime,
    _parses_as_real,
    _pick_primary,
    _read_table,
    _resolve_companion_name,
    _resolve_files,
    below_minimum,
    build_dataset_object,
    infer_column_types,
    load_companion_split,
    load_dataset,
    normalize_missing_values,
    verify_dataset,
)
from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    ProvenanceConfidence,
    Task,
)
from synthaudit_bench.model.records import (
    DatasetRecord,
    License,
    Loader,
    Source,
    Transparency,
)
from synthaudit_bench.schemas.errors import SchemaValidationError


def _record(
    dataset_id: str = "ds-a",
    *,
    target: str | None = "grade",
    test_split: str | None = None,
    fmt: str = "csv",
    header: Any = None,
    sha: dict[str, str] | None = None,
) -> DatasetRecord:
    filename = f"{dataset_id}.csv"
    return DatasetRecord(
        id=dataset_id,
        title="T",
        frame_stratum=FrameStratum.PLANTED,
        domain="energy",
        generator_family=GeneratorFamily.RULE_BASED,
        provenance_confidence=ProvenanceConfidence.DOCUMENTED,
        task=Task.CLASSIFICATION,
        target=target,
        license=License(name="CC0 1.0", redistribute=True, fetch_scriptable=True),
        source=Source(
            urls=(f"https://example.org/{filename}",),
            sha256=MappingProxyType(sha if sha is not None else {filename: "a" * 64}),
            retrieved="2026-07-23",
        ),
        loader=Loader(format=fmt, header=header),
        transparency=Transparency(True, True, True, True),
        citation="c",
        test_split=test_split,
    )


def _write_csv(path: Path, *, rows: int = 250, cols: int = 4) -> Path:
    header = ",".join(["id", "amount", "when", "grade"][:cols])
    lines = [header]
    for i in range(rows):
        cells = [str(1000 + i), f"{i}.5", f"2021-01-0{(i % 9) + 1}", "A" if i % 2 else "B"][:cols]
        lines.append(",".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# constants and enum                                                          #
# --------------------------------------------------------------------------- #


def test_constants() -> None:
    assert load.MISSING_MARKERS == ("", "NA", "NaN", "null")
    assert (MIN_ROWS, MIN_COLS) == (200, 4)
    assert [t.value for t in LogicalType] == ["numeric", "datetime", "identifier", "categorical"]


# --------------------------------------------------------------------------- #
# missing / parse predicates                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", [None, float("nan"), "", "NA", "NaN", "null"])
def test_is_missing_true(value: Any) -> None:
    assert _is_missing(value) is True


@pytest.mark.parametrize("value", ["0", "x", 5, 1.5])
def test_is_missing_false(value: Any) -> None:
    assert _is_missing(value) is False


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", True),
        ("1.5", True),
        ("-2e3", True),
        ("inf", False),
        ("nan", False),
        ("x", False),
        ("", False),
    ],
)
def test_parses_as_real(text: str, expected: bool) -> None:
    assert _parses_as_real(text) is expected


@pytest.mark.parametrize(
    "text,expected",
    [("2021-01-01", True), ("2021-01-01T12:30:00", True), ("12:30:00", False), ("x", False)],
)
def test_parses_as_datetime(text: str, expected: bool) -> None:
    assert _parses_as_datetime(text) is expected


# --------------------------------------------------------------------------- #
# infer_column_types (Appendix D.5)                                           #
# --------------------------------------------------------------------------- #


def test_infer_numeric_datetime_categorical() -> None:
    table = pd.DataFrame(
        {
            "num": ["1", "2", "3"],
            "dt": ["2021-01-01", "2021-02-01", ""],
            "cat": ["a", "b", "a"],
            "empty": ["", "NA", "null"],
        }
    )
    types = infer_column_types(table)
    assert types == {
        "num": LogicalType.NUMERIC,
        "dt": LogicalType.DATETIME,
        "cat": LogicalType.CATEGORICAL,
        "empty": LogicalType.CATEGORICAL,
    }


def test_infer_identifier_high_cardinality() -> None:
    table = pd.DataFrame({"k": [f"u{i}" for i in range(1200)]})
    assert infer_column_types(table)["k"] is LogicalType.IDENTIFIER


def test_infer_high_cardinality_but_low_ratio_is_categorical() -> None:
    values = [f"u{i}" for i in range(1001)] + [f"u{i % 1001}" for i in range(1500)]
    table = pd.DataFrame({"k": values})  # distinct 1001 > 1000 but ratio < 0.5
    assert infer_column_types(table)["k"] is LogicalType.CATEGORICAL


def test_infer_numeric_precedence_over_identifier() -> None:
    table = pd.DataFrame({"k": [str(i) for i in range(1200)]})  # distinct ints
    assert infer_column_types(table)["k"] is LogicalType.NUMERIC


# --------------------------------------------------------------------------- #
# normalization and minimums                                                  #
# --------------------------------------------------------------------------- #


def test_normalize_missing_values_is_non_mutating() -> None:
    table = pd.DataFrame({"a": ["1", "NA", "null"], "b": ["", "x", "NaN"]})
    result = normalize_missing_values(table)
    assert int(result.isna().sum().sum()) == 4
    assert result.loc[0, "a"] == "1"
    assert int(table.isna().sum().sum()) == 0  # original untouched


@pytest.mark.parametrize(
    "rows,cols,expected",
    [(250, 4, False), (199, 4, True), (250, 3, True), (10, 10, True)],
)
def test_below_minimum(rows: int, cols: int, expected: bool) -> None:
    table = pd.DataFrame({f"c{j}": list(range(rows)) for j in range(cols)})
    assert below_minimum(table) is expected


# --------------------------------------------------------------------------- #
# header mapping                                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, 0),
        (True, 0),
        (False, None),
        (0, 0),
        (2, 2),
        ("true", 0),
        ("infer", 0),
        ("false", None),
        ("none", None),
        ("", None),
        ("3", 3),
        ("weird", 0),
    ],
)
def test_header_param(header: Any, expected: int | None) -> None:
    assert _header_param(Loader(format="csv", header=header)) == expected


# --------------------------------------------------------------------------- #
# _read_table                                                                 #
# --------------------------------------------------------------------------- #


def test_read_table_faithful(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv", rows=3)
    frame = _read_table(csv, Loader(format="csv"))
    assert list(frame.columns) == ["id", "amount", "when", "grade"]
    assert frame.iloc[0]["id"] == "1000"


def test_read_table_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFormatError, match="csv"):
        _read_table(tmp_path / "x.parquet", Loader(format="parquet"))


def test_read_table_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MissingFileError, match="not found"):
        _read_table(tmp_path / "nope.csv", Loader(format="csv"))


def test_read_table_malformed_is_ingest_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(IngestError, match="failed to parse"):
        _read_table(empty, Loader(format="csv"))


def test_read_table_headerless_columns_are_strings(tmp_path: Path) -> None:
    path = tmp_path / "h.csv"
    path.write_text("1,2,3\n4,5,6\n", encoding="utf-8")
    frame = _read_table(path, Loader(format="csv", header=False))
    assert list(frame.columns) == ["0", "1", "2"]


# --------------------------------------------------------------------------- #
# file resolution                                                             #
# --------------------------------------------------------------------------- #


def test_pick_primary_prefers_id_csv() -> None:
    assert _pick_primary(_record("ds-a"), ["other.csv", "ds-a.csv"]) == "ds-a.csv"


def test_pick_primary_single_and_sorted_csv() -> None:
    assert _pick_primary(_record("x"), ["b.csv", "a.csv"]) == "a.csv"


def test_pick_primary_non_csv_fallback() -> None:
    assert _pick_primary(_record("x"), ["b.dat", "a.dat"]) == "a.dat"


def test_pick_primary_empty_is_none() -> None:
    assert _pick_primary(_record("x"), []) is None


def test_resolve_companion_direct_key(tmp_path: Path) -> None:
    files = {"t.csv": tmp_path / "t.csv"}
    assert _resolve_companion_name(_record(test_split="t.csv"), files) == "t.csv"


def test_resolve_companion_csv_suffix(tmp_path: Path) -> None:
    files = {"t.csv": tmp_path / "t.csv"}
    assert _resolve_companion_name(_record(test_split="t"), files) == "t.csv"


def test_resolve_companion_stem_match(tmp_path: Path) -> None:
    files = {"companion.data": tmp_path / "companion.data"}
    assert _resolve_companion_name(_record(test_split="companion"), files) == "companion.data"


def test_resolve_companion_ambiguous(tmp_path: Path) -> None:
    files = {"t.a": tmp_path / "t.a", "t.b": tmp_path / "t.b"}
    with pytest.raises(MissingFileError, match="not found"):
        _resolve_companion_name(_record(test_split="t"), files)


def test_resolve_companion_absent(tmp_path: Path) -> None:
    with pytest.raises(MissingFileError):
        _resolve_companion_name(_record(test_split="zzz"), {"a.csv": tmp_path / "a.csv"})


def test_resolve_files_pool_fallback(tmp_path: Path) -> None:
    # declared sha filename not among provided files -> pool falls back to files keys
    record = _record("ds-a", sha={"declared.csv": "a" * 64})
    files = {"actual.csv": tmp_path / "actual.csv"}
    primary, companion = _resolve_files(record, files)
    assert primary == tmp_path / "actual.csv"
    assert companion is None


def test_resolve_files_no_primary(tmp_path: Path) -> None:
    record = _record("ds-a", test_split="t")
    files = {"t.csv": tmp_path / "t.csv"}  # only the companion is present
    with pytest.raises(MissingFileError, match="no primary data file"):
        _resolve_files(record, files)


# --------------------------------------------------------------------------- #
# build_dataset_object                                                        #
# --------------------------------------------------------------------------- #


def test_build_dataset_object_ok() -> None:
    table = pd.DataFrame({"grade": ["A"], "x": ["1"]})
    obj = build_dataset_object(_record(), table)
    assert obj.name == "ds-a"
    assert obj.target == "grade"


def test_build_dataset_object_missing_target_raises() -> None:
    table = pd.DataFrame({"x": ["1"]})
    with pytest.raises(IngestError, match="not a column"):
        build_dataset_object(_record(target="grade"), table)


# --------------------------------------------------------------------------- #
# companion split loading                                                     #
# --------------------------------------------------------------------------- #


def test_load_companion_split_ok(tmp_path: Path) -> None:
    test_csv = _write_csv(tmp_path / "ds-a-test.csv", rows=5)
    record = _record(test_split="ds-a-test")
    frame = load_companion_split(record, {"ds-a-test.csv": test_csv})
    assert frame.shape[0] == 5


def test_load_companion_split_none_raises() -> None:
    with pytest.raises(IngestError, match="no test_split"):
        load_companion_split(_record(test_split=None), {})


def test_load_companion_split_missing(tmp_path: Path) -> None:
    with pytest.raises(MissingFileError):
        load_companion_split(_record(test_split="ds-a-test"), {})


# --------------------------------------------------------------------------- #
# load_dataset                                                                #
# --------------------------------------------------------------------------- #


def test_load_dataset_primary_only(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    obj = load_dataset(_record(), {"ds-a.csv": csv})
    assert obj.n_rows == 250
    assert obj.columns == ("id", "amount", "when", "grade")
    assert obj.has_test is False


def test_load_dataset_with_companion(tmp_path: Path) -> None:
    primary = _write_csv(tmp_path / "ds-a.csv")
    companion = _write_csv(tmp_path / "ds-a-test.csv", rows=210)
    record = _record(test_split="ds-a-test")
    obj = load_dataset(record, {"ds-a.csv": primary, "ds-a-test.csv": companion})
    assert obj.has_test is True
    assert obj.test_table is not None
    assert obj.test_table.shape[0] == 210


def test_load_dataset_expected_hash_ok(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    digest = sha256_bytes(csv.read_bytes())
    obj = load_dataset(_record(), {"ds-a.csv": csv}, expected_hash=digest.upper())
    assert obj.content_hash() == digest


def test_load_dataset_expected_hash_mismatch(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    with pytest.raises(ChecksumError, match="does not match expected"):
        load_dataset(_record(), {"ds-a.csv": csv}, expected_hash="0" * 64)


# --------------------------------------------------------------------------- #
# verify_dataset                                                              #
# --------------------------------------------------------------------------- #


def test_verify_dataset_ok(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    digest = sha256_bytes(csv.read_bytes())
    record = _record(sha={"ds-a.csv": digest})
    report = verify_dataset(record, {"ds-a.csv": csv}, expected_content_hash=digest)
    assert isinstance(report, VerificationReport)
    assert report.files_verified == ("ds-a.csv",)
    assert report.content_hash == digest
    assert report.target == "grade"
    assert report.has_companion is False
    assert report.to_mapping()["dataset_id"] == "ds-a"


def test_verify_dataset_schema_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")

    def _boom(name: str, instance: Any, version: str | None = None) -> None:
        raise SchemaValidationError(
            schema_id="dataset", pointer="/id", value="bad", explanation="not valid"
        )

    monkeypatch.setattr("synthaudit_bench.load.schemas.validate_instance", _boom)
    with pytest.raises(InvalidMetadataError, match="failed schema validation"):
        verify_dataset(_record(), {"ds-a.csv": csv})


def test_verify_dataset_checksum_failure(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    record = _record(sha={"ds-a.csv": "0" * 64})
    with pytest.raises(ChecksumError):
        verify_dataset(record, {"ds-a.csv": csv})


def test_verify_dataset_missing_file() -> None:
    record = _record(sha={"ds-a.csv": "a" * 64})
    with pytest.raises(MissingFileError):
        verify_dataset(record, {})


def test_verify_dataset_content_hash_mismatch(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "ds-a.csv")
    digest = sha256_bytes(csv.read_bytes())
    record = _record(sha={"ds-a.csv": digest})
    with pytest.raises(ChecksumError, match="does not match expected"):
        verify_dataset(record, {"ds-a.csv": csv}, expected_content_hash="0" * 64)


def test_ingest_error_hierarchy() -> None:
    for exc in (InvalidMetadataError, UnsupportedFormatError, MissingFileError):
        assert issubclass(exc, IngestError)

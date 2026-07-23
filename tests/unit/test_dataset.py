"""Unit tests for the loaded-dataset domain object."""

from __future__ import annotations

import dataclasses
import hashlib

import pandas as pd
import pytest

from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.records import DatasetRecord


def _df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3], "stabf": ["x", "y", "x"]})


def test_shape_and_columns() -> None:
    obj = DatasetObject(name="grid", table=_df(), target="stabf")
    assert obj.n_rows == 3
    assert obj.n_cols == 2
    assert obj.columns == ("a", "stabf")
    assert obj.has_test is False


def test_content_hash_is_table_canonical_csv() -> None:
    obj = DatasetObject(name="grid", table=_df())
    expected = hashlib.sha256(_df().to_csv(index=False, lineterminator="\n").encode("utf-8"))
    assert obj.content_hash() == expected.hexdigest()
    assert isinstance(obj.to_canonical(), bytes)
    assert len(obj.content_hash()) == 64


def test_content_hash_changes_with_content() -> None:
    a = DatasetObject(name="x", table=pd.DataFrame({"a": [1]}))
    b = DatasetObject(name="x", table=pd.DataFrame({"a": [2]}))
    assert a.content_hash() != b.content_hash()


def test_bad_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a column"):
        DatasetObject(name="x", table=_df(), target="nope")


def test_equality_is_content_based() -> None:
    a = DatasetObject(name="x", table=_df(), target="stabf")
    b = DatasetObject(name="x", table=_df(), target="stabf")
    assert a == b
    assert a != DatasetObject(name="y", table=_df(), target="stabf")
    assert a != DatasetObject(name="x", table=_df())  # different target
    assert (a == 5) is False


def test_test_table_equality_and_summary() -> None:
    a = DatasetObject(name="x", table=_df(), test_table=_df())
    b = DatasetObject(name="x", table=_df(), test_table=_df())
    assert a == b
    assert a.has_test is True
    assert a != DatasetObject(name="x", table=_df())  # one has a test table
    summary = a.to_mapping()
    assert summary["n_rows"] == 3
    assert summary["has_test"] is True
    assert "content_hash" in summary
    assert len(a.summary_hash()) == 64


def test_dataset_object_is_frozen() -> None:
    obj = DatasetObject(name="x", table=_df())
    with pytest.raises(dataclasses.FrozenInstanceError):
        obj.name = "y"  # type: ignore[misc]


def test_summary_includes_record_id(dataset_record: DatasetRecord) -> None:
    obj = DatasetObject(name="grid", table=_df(), target="stabf", record=dataset_record)
    assert obj.to_mapping()["record_id"] == "grid-stability-uci"

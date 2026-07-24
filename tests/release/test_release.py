"""Unit tests for release manifest generation, version reporting, and semver policy."""

from __future__ import annotations

import pandas as pd
import pytest

from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.release import (
    build_release_manifest,
    check_version_bump,
    dataset_manifest_entry,
    version_report,
)


def _dataset(name: str) -> DatasetObject:
    table = pd.DataFrame({"a": ["1", "2"], "b": ["x", "y"]})
    return DatasetObject(name=name, table=table)


def test_version_report() -> None:
    report = version_report()
    assert report["benchmark"] == "1.0.0"
    assert report["software"]
    assert "1.0.0" in report["schemas"]


def test_dataset_manifest_entry() -> None:
    entry = dataset_manifest_entry(
        _dataset("d1"), corpus="evaluation", license="CC0", source=("u",), split="public-dev"
    )
    mapping = entry.to_mapping()
    assert mapping["id"] == "d1"
    assert mapping["n_rows"] == 2
    assert mapping["n_cols"] == 2
    assert mapping["byte_size"] > 0
    assert mapping["sha256"] == _dataset("d1").content_hash()
    assert mapping["split"] == "public-dev"


def test_build_release_manifest_sorted() -> None:
    entries = [
        dataset_manifest_entry(_dataset("d-b"), corpus="census", license="CC0", source=()),
        dataset_manifest_entry(_dataset("d-a"), corpus="census", license="CC0", source=()),
    ]
    manifest = build_release_manifest(entries, reproducibility_note="asymmetry noted")
    assert [d["id"] for d in manifest["datasets"]] == ["d-a", "d-b"]
    assert manifest["reproducibility_note"] == "asymmetry noted"
    assert manifest["benchmark_version"] == "1.0.0"


@pytest.mark.parametrize(
    "current,previous,change,expected",
    [
        ("2.0.0", "1.4.2", "major", True),
        ("1.1.0", "1.0.0", "minor", True),
        ("1.0.1", "1.0.0", "patch", True),
        ("1.1.0", "1.0.0", "major", False),
        ("1.0.0", "1.0.0", "patch", False),
        ("2.0.0", "1.0.0", "minor", False),
        ("1.0.0", "1.0.0", "unknown", False),
        ("bad", "1.0.0", "major", False),
    ],
)
def test_check_version_bump(current: str, previous: str, change: str, expected: bool) -> None:
    assert check_version_bump(current, previous, change) is expected

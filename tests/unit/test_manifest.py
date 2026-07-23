"""Unit tests for the run manifest and its provenance value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.config import ResourceLimits
from synthaudit_bench.model.manifest import (
    DatasetEntry,
    Environment,
    RunManifest,
    Timestamps,
)
from synthaudit_bench.model.results import DetectorInfo

_DET = DetectorInfo(name="synthaudit", version="0.1.0")
_ENV = Environment(
    python_version="3.11.9",
    platform="linux",
    dependencies={"pandas": "2.2.0", "numpy": "1.26.0"},
)
_TS = Timestamps(started_at="2026-07-23T00:00:00Z", finished_at="2026-07-23T00:05:00Z")


def _manifest(**overrides: object) -> RunManifest:
    base: dict[str, object] = {
        "bench_version": "1.0.0",
        "sto_version": "1.0.0",
        "schema_version": "1.0.0",
        "split": "public-dev",
        "detector": _DET,
        "config_hash": "c0ffee",
        "environment": _ENV,
        "root_seed": 42,
        "limits": ResourceLimits(wall_clock_s=60.0),
        "timestamps": _TS,
        "datasets": (
            DatasetEntry(dataset_id="grid", sha256="h" * 64, status="ok", result_hash="r"),
        ),
    }
    base.update(overrides)
    return RunManifest(**base)  # type: ignore[arg-type]


def test_environment_round_trip_and_hash() -> None:
    assert Environment.from_mapping(_ENV.to_mapping()) == _ENV
    # dependencies serialize in sorted key order
    assert list(_ENV.to_mapping()["dependencies"]) == ["numpy", "pandas"]
    assert len(_ENV.env_hash()) == 64


def test_dataset_entry_round_trip_with_and_without_result_hash() -> None:
    full = DatasetEntry(dataset_id="d", sha256="h", status="ok", result_hash="r")
    assert DatasetEntry.from_mapping(full.to_mapping()) == full
    failed = DatasetEntry(dataset_id="d", sha256="h", status="failed")
    assert "result_hash" not in failed.to_mapping()
    assert DatasetEntry.from_mapping(failed.to_mapping()) == failed


def test_timestamps_round_trip() -> None:
    assert Timestamps.from_mapping(_TS.to_mapping()) == _TS


def test_manifest_minimal_and_full_round_trip() -> None:
    assert RunManifest.from_mapping(_manifest().to_mapping()) == _manifest()
    full = _manifest(held_out_seeds=(1, 2, 3), pin_overrides=("sto_version",))
    assert RunManifest.from_mapping(full.to_mapping()) == full


def test_datasets_normalized_to_sorted_order() -> None:
    manifest = _manifest(
        datasets=(
            DatasetEntry(dataset_id="zebra", sha256="h", status="ok"),
            DatasetEntry(dataset_id="alpha", sha256="h", status="ok"),
        )
    )
    assert [d.dataset_id for d in manifest.datasets] == ["alpha", "zebra"]


def test_content_hash_excludes_timestamps() -> None:
    a = _manifest(timestamps=Timestamps("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"))
    b = _manifest(timestamps=Timestamps("2027-12-31T23:59:59Z", "2028-01-01T00:00:00Z"))
    assert a.content_hash() == b.content_hash()
    assert a.to_mapping()["timestamps"]["started_at"] == "2026-01-01T00:00:00Z"
    assert isinstance(a.to_canonical(), bytes)


def test_content_hash_is_content_addressed() -> None:
    assert _manifest().content_hash() != _manifest(config_hash="beef").content_hash()
    assert _manifest().content_hash() != _manifest(held_out_seeds=(9,)).content_hash()
    assert len(_manifest().content_hash()) == 64


def test_manifest_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _manifest().split = "held-out"  # type: ignore[misc]

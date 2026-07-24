"""Unit and integration tests for the batch execution engine."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from _runhelpers import ConstDetector, ErrorDetector, make_dataset, mapper

from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.manifest import Environment, Timestamps
from synthaudit_bench.runner import (
    FileResultCache,
    InMemoryJournal,
    IntegrityAbort,
    RunEvent,
    capture_environment,
    run_benchmark,
    run_id,
    write_artifacts,
)

_DATASETS = [make_dataset("d-b"), make_dataset("d-a"), make_dataset("d-c")]


def test_run_orders_results_and_builds_manifest() -> None:
    outcome = run_benchmark(_DATASETS, ConstDetector(), split="public-dev", mapper=mapper())
    assert [r.dataset_id for r in outcome.results] == ["d-a", "d-b", "d-c"]
    assert outcome.scored == 3
    assert outcome.failed == 0
    assert [d.status for d in outcome.manifest.datasets] == ["scored", "scored", "scored"]
    assert outcome.manifest.split == "public-dev"


def test_parallel_matches_serial() -> None:
    serial = run_benchmark(_DATASETS, ConstDetector(), split="s", mapper=mapper())
    parallel = run_benchmark(_DATASETS, ConstDetector(), split="s", mapper=mapper(), jobs=3)
    assert parallel.manifest.content_hash() == serial.manifest.content_hash()
    assert [r.content_hash() for r in parallel.results] == [
        r.content_hash() for r in serial.results
    ]


def test_error_is_isolated_not_fatal() -> None:
    outcome = run_benchmark(_DATASETS, ErrorDetector(), split="s")
    assert outcome.failed == 3
    assert all(d.status == "runtime" for d in outcome.manifest.datasets)


def test_below_minimum_status_is_scored() -> None:
    outcome = run_benchmark(
        [make_dataset("small", rows=10)], ConstDetector(), split="s", mapper=mapper()
    )
    assert outcome.results[0].notes == ("below_minimum",)
    assert outcome.manifest.datasets[0].status == "scored"


def test_cache_resume_and_relabel(tmp_path: Path) -> None:
    cache = FileResultCache(tmp_path / "cache")
    journal = InMemoryJournal()
    first = run_benchmark(
        _DATASETS, ConstDetector(), split="s", mapper=mapper(), cache=cache, journal=journal
    )
    assert not any(e.cached for e in first.events)
    second = run_benchmark(
        _DATASETS, ConstDetector(), split="s", mapper=mapper(), cache=cache, journal=journal
    )
    assert sum(e.cached for e in second.events) == 3  # every dataset reused from cache
    assert journal.completed() == {"d-a", "d-b", "d-c"}
    # identical-content datasets share a cache key; the reused result is relabeled
    shared = pd.DataFrame(
        {
            "k": ["1"] * 250,
            "b": [str(i) for i in range(250)],
            "c": [str(i) for i in range(250)],
            "grade": ["A"] * 250,
        }
    )
    twins = [
        DatasetObject(name="t-x", table=shared, target="grade"),
        DatasetObject(name="t-y", table=shared, target="grade"),
    ]
    twin_cache = FileResultCache(tmp_path / "twins")
    outcome = run_benchmark(twins, ConstDetector(), split="s", mapper=mapper(), cache=twin_cache)
    assert {r.dataset_id for r in outcome.results} == {"t-x", "t-y"}


def test_integrity_abort() -> None:
    with pytest.raises(IntegrityAbort, match="does not match expected"):
        run_benchmark(
            [make_dataset("d-a")], ConstDetector(), split="s", expected_hashes={"d-a": "0" * 64}
        )


def test_expected_hash_match_is_ok() -> None:
    dataset = make_dataset("d-a")
    outcome = run_benchmark(
        [dataset],
        ConstDetector(),
        split="s",
        mapper=mapper(),
        expected_hashes={"d-a": dataset.content_hash()},
    )
    assert outcome.scored == 1


def test_cancellation_records_remaining() -> None:
    calls = {"n": 0}

    def cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # allow the first dataset, cancel the rest

    outcome = run_benchmark(
        _DATASETS, ConstDetector(), split="s", mapper=mapper(), should_cancel=cancel
    )
    statuses = {d.dataset_id: d.status for d in outcome.manifest.datasets}
    assert statuses["d-a"] == "scored"
    assert statuses["d-b"] == "cancelled"
    assert statuses["d-c"] == "cancelled"


def test_injected_environment_and_timestamps() -> None:
    env = Environment(python_version="3.11.0", platform="linux")
    stamps = Timestamps("2026-07-24T00:00:00Z", "2026-07-24T00:01:00Z")
    outcome = run_benchmark(
        [make_dataset("d-a")],
        ConstDetector(),
        split="s",
        mapper=mapper(),
        environment=env,
        timestamps=stamps,
    )
    assert outcome.manifest.environment.python_version == "3.11.0"
    assert outcome.manifest.timestamps.finished_at == "2026-07-24T00:01:00Z"


def test_validate_false_skips_schema_check() -> None:
    outcome = run_benchmark(
        [make_dataset("d-a")], ConstDetector(), split="s", mapper=mapper(), validate=False
    )
    assert outcome.scored == 1


def test_write_artifacts(tmp_path: Path) -> None:
    outcome = run_benchmark(_DATASETS, ConstDetector(), split="s", mapper=mapper())
    paths = write_artifacts(outcome, tmp_path / "out")
    assert paths["manifest"].is_file()
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["split"] == "s"
    assert len(list((tmp_path / "out" / "audits").glob("*.json"))) == 3


def test_capture_environment_has_no_clock() -> None:
    env = capture_environment()
    assert env.python_version
    assert env.platform


def test_run_id_is_deterministic() -> None:
    outcome = run_benchmark([make_dataset("d-a")], ConstDetector(), split="s", mapper=mapper())
    again = run_id(outcome.manifest.detector, "s", "", ["d-a"])
    assert outcome.run_id == again


def test_run_event_to_mapping() -> None:
    assert RunEvent("run_start").to_mapping() == {"kind": "run_start"}
    full = RunEvent("dataset_complete", "d-a", "scored", cached=True).to_mapping()
    assert full == {
        "kind": "dataset_complete",
        "dataset_id": "d-a",
        "status": "scored",
        "cached": True,
    }

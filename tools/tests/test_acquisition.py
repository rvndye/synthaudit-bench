"""Tests for the acquisition pipeline."""

from __future__ import annotations

from pathlib import Path

from benchkit.acquisition import acquire_records

from _fixtures import FIXTURE_BYTES, dataset_record


def test_verified_acquisition_with_injected_fetcher(tmp_path: Path) -> None:
    record = dataset_record("fx-ok")

    def fetcher(url: str) -> bytes:
        return FIXTURE_BYTES

    report = acquire_records([record], tmp_path, fetcher=fetcher)
    assert report.ok
    assert report.outcomes[0].status == "verified"
    assert report.outcomes[0].verified


def test_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    record = dataset_record("fx-bad")

    def fetcher(url: str) -> bytes:
        return b"wrong,bytes\n9,9\n"

    report = acquire_records([record], tmp_path, fetcher=fetcher)
    assert not report.ok
    outcome = report.outcomes[0]
    assert outcome.status == "failed"
    assert outcome.error_code == "integrity"


def test_no_fetcher_non_redistributable_is_stub(tmp_path: Path) -> None:
    record = dataset_record("fx-stub", redistribute=False, fetch_scriptable=False)
    report = acquire_records([record], tmp_path)
    assert report.ok  # a stub is a valid, non-failing outcome
    assert report.outcomes[0].status == "stub"


def test_require_data_without_source_fails(tmp_path: Path) -> None:
    record = dataset_record("fx-req", fetch_scriptable=False, redistribute=False)
    report = acquire_records([record], tmp_path, require_data=True)
    assert not report.ok
    assert report.outcomes[0].status == "failed"


def test_report_is_deterministic(tmp_path: Path) -> None:
    records = [dataset_record("b"), dataset_record("a")]
    first = acquire_records(records, tmp_path).to_mapping()
    second = acquire_records(records, tmp_path).to_mapping()
    assert first == second
    assert [o["dataset_id"] for o in first["outcomes"]] == ["a", "b"]

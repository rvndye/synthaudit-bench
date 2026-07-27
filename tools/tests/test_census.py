"""Tests for the census enumeration pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest
from benchkit.census import CandidateInput, enumerate_candidates, stable_id
from benchkit.errors import InputError

from _fixtures import FIXTURE_BYTES, FIXTURE_SHA256


def _candidate(source_key: str, file: Path | None = None) -> CandidateInput:
    return CandidateInput(
        source_key=source_key,
        title=f"Candidate {source_key}",
        source_urls=("https://example.invalid/x",),
        retrieved="2026-01-01",
        file=file,
    )


def test_stable_id_is_deterministic_and_kebab() -> None:
    assert stable_id("Repo/Item 1") == stable_id("Repo/Item 1")
    assert stable_id("Repo/Item 1") != stable_id("Repo/Item 2")
    assert stable_id("Repo/Item 1").startswith("census-repo-item-1-")


def test_empty_input_yields_no_records() -> None:
    assert enumerate_candidates([]) == []


def test_enumerate_computes_hash_and_size(tmp_path: Path) -> None:
    data = tmp_path / "d.csv"
    data.write_bytes(FIXTURE_BYTES)
    records = enumerate_candidates([_candidate("k1", data)])
    assert len(records) == 1
    assert records[0].file_sha256 == FIXTURE_SHA256
    assert records[0].file_bytes == len(FIXTURE_BYTES)


def test_enumerate_is_deterministic_and_sorted() -> None:
    a = enumerate_candidates([_candidate("k2"), _candidate("k1")])
    b = enumerate_candidates([_candidate("k1"), _candidate("k2")])
    assert [r.to_mapping() for r in a] == [r.to_mapping() for r in b]
    assert [r.id for r in a] == sorted(r.id for r in a)


def test_duplicate_source_key_fails_closed() -> None:
    with pytest.raises(InputError, match="duplicate census id"):
        enumerate_candidates([_candidate("dup"), _candidate("dup")])


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="file not found"):
        enumerate_candidates([_candidate("k", tmp_path / "nope.csv")])


def test_no_label_or_class_is_emitted() -> None:
    record = enumerate_candidates([_candidate("k1")])[0]
    mapping = record.to_mapping()
    assert "classes" not in mapping
    assert "gold" not in mapping
    assert "disposition" not in mapping

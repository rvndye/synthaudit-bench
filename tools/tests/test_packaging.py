"""Tests for benchmark packaging."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from benchkit.errors import ReproducibilityError
from benchkit.packaging import release_checksums, validate_release, verify_reproducible

from _fixtures import FIXTURE_BYTES, record_mapping


def _registry(tmp_path: Path, *dataset_ids: str) -> Path:
    root = tmp_path / "registry"
    (root / "census").mkdir(parents=True)
    for did in dataset_ids:
        (root / "census" / f"{did}.yaml").write_text(
            yaml.safe_dump(record_mapping(did)), encoding="utf-8"
        )
    return root


def test_valid_release_passes(tmp_path: Path) -> None:
    result = validate_release(_registry(tmp_path, "fx-1", "fx-2"))
    assert result.ok
    assert result.counts["records"] == 2


def test_gold_without_record_is_referential_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path, "fx-1")
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "orphan.json").write_text(
        json.dumps(
            [
                {
                    "support": ["a"],
                    "classes": ["STO-S02"],
                    "dispositions": ["not_applicable"],
                    "gold_type": "objective",
                    "evidence": "x",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = validate_release(registry, gold_dir=gold)
    assert not result.ok
    assert result.rules["gold_referential"] is False


def test_split_overlap_is_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path, "fx-1", "fx-2")
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"public-dev": ["fx-1"], "held-out": ["fx-1"]}), encoding="utf-8")
    result = validate_release(registry, splits_path=splits)
    assert not result.ok
    assert result.rules["split_integrity"] is False


def test_split_unknown_id_is_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path, "fx-1")
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"public-dev": ["missing"], "held-out": []}), encoding="utf-8")
    result = validate_release(registry, splits_path=splits)
    assert not result.ok
    assert result.rules["split_integrity"] is False


def test_checksums_are_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "d.csv"
    f.write_bytes(FIXTURE_BYTES)
    assert release_checksums({"d.csv": f}) == release_checksums({"d.csv": f})


def test_verify_reproducible_true_and_false() -> None:
    assert verify_reproducible(lambda: {"a": 1, "b": [1, 2]})

    state = {"n": 0}

    def unstable() -> dict[str, int]:
        state["n"] += 1
        return {"n": state["n"]}

    with pytest.raises(ReproducibilityError):
        verify_reproducible(unstable)

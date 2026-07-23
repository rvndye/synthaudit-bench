"""Disk-based registry tests: loading, caching, splits and manifest files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from synthaudit_bench import registry as reg
from synthaudit_bench.registry.loader import _normalize_manifest, _normalize_splits, _read_yaml


def _rec(
    dataset_id: str, *, stratum: str = "census", family: str = "physics-simulator"
) -> dict[str, Any]:
    return {
        "id": dataset_id,
        "title": dataset_id.title(),
        "frame_stratum": stratum,
        "domain": "energy",
        "generator_family": family,
        "provenance_confidence": "documented",
        "modality": "tabular",
        "task": "classification",
        "target": "y",
        "license": {"name": "CC0 1.0", "redistribute": True, "fetch_scriptable": True},
        "source": {
            "urls": ["https://example.org/x.csv"],
            "sha256": {"x.csv": "a" * 64},
            "retrieved": "2026-07-23",
        },
        "loader": {"format": "csv"},
        "transparency": {
            "generator_described": True,
            "generator_code_available": False,
            "seed_reported": True,
            "artifacts_disclosed": False,
        },
        "citation": "Example 2026",
    }


def _write(root: Path, corpus: str, record: dict[str, Any]) -> None:
    directory = root / corpus
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{record['id']}.yaml").write_text(json.dumps(record), encoding="utf-8")


def _make_registry(
    tmp_path: Path, *, with_splits: bool = True, with_manifest: bool = False
) -> Path:
    root = tmp_path / "registry"
    _write(root, "census", _rec("grid"))
    _write(root, "evaluation", _rec("planted-1", stratum="planted", family="rule-based"))
    if with_splits:
        (root / "evaluation" / "splits.json").write_text(
            json.dumps({"public-dev": ["planted-1"]}), encoding="utf-8"
        )
    if with_manifest:
        (root / "MANIFEST.json").write_text(
            json.dumps({"datasets": [{"id": "grid", "sha256": "h" * 64}]}), encoding="utf-8"
        )
    return root


# --- loading from disk ----------------------------------------------------------


def test_load_registry_discovers_and_assigns(tmp_path: Path) -> None:
    root = _make_registry(tmp_path, with_manifest=True)
    r = reg.load_registry(root, use_cache=False)
    assert r.ids() == ("grid", "planted-1")
    assert r.get("planted-1").split is reg.Split.PUBLIC_DEV
    assert r.get("grid").content_hash == "h" * 64
    assert reg.referential_integrity(r).ok is True


def test_load_registry_without_splits_or_manifest(tmp_path: Path) -> None:
    root = _make_registry(tmp_path, with_splits=False)
    # only a census dataset present; evaluation dataset would need a split, so drop it
    (root / "evaluation" / "planted-1.yaml").unlink()
    r = reg.load_registry(root, use_cache=False)
    assert r.ids() == ("grid",)
    assert r.get("grid").split is None


def test_load_registry_is_cached_by_path(tmp_path: Path) -> None:
    root = _make_registry(tmp_path)
    assert reg.load_registry(root) is reg.load_registry(root)
    assert reg.load_registry(root, use_cache=False) is not reg.load_registry(root, use_cache=False)


def test_mapping_splits_bypass_cache_and_apply(tmp_path: Path) -> None:
    root = _make_registry(tmp_path, with_splits=False)
    r = reg.load_registry(root, splits={"planted-1": "held-out"})
    assert r.get("planted-1").split is reg.Split.HELD_OUT


def test_explicit_splits_and_manifest_paths(tmp_path: Path) -> None:
    root = _make_registry(tmp_path, with_splits=False)
    splits_path = tmp_path / "s.json"
    splits_path.write_text(json.dumps({"planted-1": "public-dev"}), encoding="utf-8")
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text(json.dumps({"grid": {"sha256": "h" * 64}}), encoding="utf-8")
    r = reg.load_registry(root, splits=splits_path, manifest=manifest_path, use_cache=False)
    assert r.get("planted-1").split is reg.Split.PUBLIC_DEV
    assert r.get("grid").content_hash == "h" * 64


def test_validate_registry_from_path(tmp_path: Path) -> None:
    root = _make_registry(tmp_path)
    validated = reg.validate_registry(root, sto_version="1.0.0", schema_version="1.0.0")
    assert validated.ids() == ("grid", "planted-1")


def test_non_mapping_record_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(reg.InvalidRecordError, match="not a mapping"):
        _read_yaml(path)


# --- splits and manifest normalization ------------------------------------------


def test_normalize_splits_forms() -> None:
    assert _normalize_splits({"public-dev": ["a", "b"], "held-out": ["c"]}) == {
        "a": "public-dev",
        "b": "public-dev",
        "c": "held-out",
    }
    assert _normalize_splits({"a": "public-dev"}) == {"a": "public-dev"}
    with pytest.raises(reg.RegistryError, match="splits must be a mapping"):
        _normalize_splits(["a", "b"])


def test_normalize_manifest_forms() -> None:
    assert _normalize_manifest({"datasets": [{"id": "a", "sha256": "h"}]}) == {"a": "h"}
    assert _normalize_manifest({"a": {"sha256": "h"}}) == {"a": "h"}
    assert _normalize_manifest({"a": "h"}) == {"a": "h"}
    with pytest.raises(reg.RegistryError, match="manifest must be"):
        _normalize_manifest("not valid")


# --- the committed illustrative registry ----------------------------------------


def test_committed_registry_is_valid() -> None:
    root = Path(__file__).resolve().parents[2] / "registry"
    validated = reg.validate_registry(root, sto_version="1.0.0", schema_version="1.0.0")
    corpora = {entry.corpus for entry in validated}
    assert corpora == {
        reg.Corpus.CENSUS,
        reg.Corpus.EVALUATION,
        reg.Corpus.CONTROLLED,
        reg.Corpus.CONFORMANCE,
    }
    assert len(reg.enumerate_corpus(validated, "evaluation")) == 2

"""Remaining branch coverage for the registry subsystem."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from synthaudit_bench import registry as reg
from synthaudit_bench.registry.integrity import _version_supported


def _rec(dataset_id: str, *, stratum: str = "census") -> dict[str, Any]:
    return {
        "id": dataset_id,
        "title": dataset_id,
        "frame_stratum": stratum,
        "domain": "energy",
        "generator_family": "physics-simulator",
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


def test_version_supported_skips_unparseable_candidate() -> None:
    assert _version_supported("1.0.0", ("garbage", "1.0.0")) is True
    assert _version_supported("1.0.0", ("garbage",)) is False


def test_datasets_and_no_hash_serialization() -> None:
    r = reg.build_registry([(_rec("nohash"), "census")])
    assert r.datasets() == r.entries
    assert "content_hash" not in r.get("nohash").to_mapping()


def test_integrity_report_serializes_issues() -> None:
    r = reg.build_registry([(_rec("eval-nosplit", stratum="planted"), "evaluation")])
    report = reg.referential_integrity(r)
    mapping = report.to_mapping()
    assert mapping["ok"] is False
    assert mapping["issues"][0]["code"] == "missing_split"
    assert mapping["issues"][0]["dataset_id"] == "eval-nosplit"


def test_load_registry_with_manifest_mapping(tmp_path: Path) -> None:
    root = tmp_path / "registry"
    (root / "census").mkdir(parents=True)
    (root / "census" / "grid.yaml").write_text(json.dumps(_rec("grid")), encoding="utf-8")
    r = reg.load_registry(root, manifest={"grid": "h" * 64})
    assert r.get("grid").content_hash == "h" * 64

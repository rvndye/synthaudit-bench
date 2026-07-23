"""Edge-case coverage for the configuration subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from synthaudit_bench import config as cfg
from synthaudit_bench.config.loader import read_yaml_file, resolve_thresholds


def _thresholds(sto_version: str) -> tuple[dict[str, Any], str]:
    return {"sto_version": sto_version, "matching": {"tau_jaccard": 0.5}}, "test"


def test_resolve_uses_packaged_thresholds_by_default() -> None:
    # No thresholds_loader => the packaged STO-1.0.0 operating points are used.
    base = cfg.ConfigLayer(
        "packaged-defaults", cfg.packaged_defaults(), kind="packaged", is_base=True
    )
    resolved = cfg.resolve_config([base])
    assert resolved.config.thresholds["matching"]["tau_jaccard"] == 0.5
    assert resolved.provenance.threshold_source.startswith("packaged:")


def test_empty_yaml_file_is_an_empty_mapping(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("# only a comment\n", encoding="utf-8")
    assert read_yaml_file(path) == {}


def test_thresholds_fall_back_to_packaged_when_root_lacks_them(tmp_path: Path) -> None:
    # config_root is given but has no thresholds/ dir => packaged fallback.
    thresholds, source = resolve_thresholds("1.0.0", tmp_path)
    assert thresholds["matching"]["tau_jaccard"] == 0.5
    assert source.startswith("packaged:")


def test_pin_override_of_absent_pin_records_none_previous() -> None:
    base = cfg.ConfigLayer(
        "packaged-defaults",
        {
            "pins": {"sto_version": "1.0.0", "schema_versions": {"dataset": "1.0.0"}},
            "root_seed": 42,
            "limits": {"wall_clock_s": 1, "memory_mb": 1},
            "log_level": "INFO",
        },
        kind="packaged",
        is_base=True,
    )
    override = cfg.ConfigLayer("cli", {"pins": {"bench_version": "1.0.0"}}, kind="cli")
    resolved = cfg.resolve_config(
        [base, override], thresholds_loader=_thresholds, allow_pin_override=True
    )
    assert resolved.provenance.pin_overrides[0].previous is None


def test_provenance_to_mapping_serializes_pin_overrides() -> None:
    base = cfg.ConfigLayer(
        "packaged-defaults", cfg.packaged_defaults(), kind="packaged", is_base=True
    )
    override = cfg.ConfigLayer("cli", {"pins": {"bench_version": "2.0.0"}}, kind="cli")
    resolved = cfg.resolve_config(
        [base, override], thresholds_loader=_thresholds, allow_pin_override=True
    )
    mapping = resolved.to_mapping()
    assert mapping["provenance"]["pin_overrides"] == [
        {"path": "pins.bench_version", "previous": "1.0.0", "new": "2.0.0", "layer": "cli"}
    ]
    # layer contributions serialize too
    assert any(layer["kind"] == "cli" for layer in mapping["provenance"]["layers"])

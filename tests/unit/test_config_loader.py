"""Unit tests for configuration loading: files, profiles, thresholds, environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from synthaudit_bench import config as cfg
from synthaudit_bench.config.loader import read_yaml_file, resolve_thresholds

_DEFAULT_YAML = """
pins:
  bench_version: "1.0.0"
  sto_version: "1.0.0"
  synthaudit_version: "0.1.0"
  thresholds_ref: "STO-1.0.0"
  schema_versions: {dataset: "1.0.0", config: "1.0.0"}
root_seed: 42
limits: {wall_clock_s: 1800, memory_mb: 8192}
log_level: "INFO"
"""


def _make_root(tmp_path: Path, *, with_default: bool = True, with_thresholds: bool = False) -> Path:
    root = tmp_path / "configs"
    (root / "profiles").mkdir(parents=True)
    if with_default:
        (root / "default.yaml").write_text(_DEFAULT_YAML, encoding="utf-8")
    (root / "profiles" / "ci.yaml").write_text("jobs: 2\nlog_level: WARNING\n", encoding="utf-8")
    if with_thresholds:
        (root / "thresholds").mkdir()
        (root / "thresholds" / "STO-1.0.0.yaml").write_text(
            "sto_version: '1.0.0'\nmatching: {tau_jaccard: 0.7}\n", encoding="utf-8"
        )
    return root


# --- loader helpers -------------------------------------------------------------


def test_packaged_defaults_are_independent_copies() -> None:
    a = cfg.packaged_defaults()
    a["root_seed"] = 999
    assert cfg.packaged_defaults()["root_seed"] == 42


def test_parse_env_filters_prefix_and_types_scalars() -> None:
    env = {
        "SAB_ROOT_SEED": "7",
        "SAB_LIMITS__WALL_CLOCK_S": "30",
        "SAB_LOG_LEVEL": "DEBUG",
        "PATH": "/usr/bin",
    }
    parsed = cfg.parse_env(env)
    assert parsed == {"root_seed": 7, "limits": {"wall_clock_s": 30}, "log_level": "DEBUG"}


def test_expand_dotted_handles_dotted_and_nested() -> None:
    assert cfg.expand_dotted({"a.b": 1, "c": 2}) == {"a": {"b": 1}, "c": 2}
    assert cfg.expand_dotted({"a": {"b.c": 3}}) == {"a": {"b": {"c": 3}}}


def test_read_yaml_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(cfg.ConfigError, match="not a mapping"):
        read_yaml_file(path)


def test_read_yaml_missing_file(tmp_path: Path) -> None:
    with pytest.raises(cfg.ConfigError, match="not found"):
        read_yaml_file(tmp_path / "nope.yaml")


def test_load_thresholds_from_package_data() -> None:
    thresholds = cfg.load_thresholds("1.0.0")
    assert thresholds["matching"]["tau_jaccard"] == 0.5
    assert thresholds["bti"]["grade_bands"]["A"] == 0.80
    _, source = resolve_thresholds("1.0.0")
    assert source.startswith("packaged:")


def test_load_thresholds_missing_version_raises() -> None:
    with pytest.raises(cfg.ConfigError, match="no thresholds"):
        cfg.load_thresholds("9.9.9")


def test_load_profile_unknown_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path)
    with pytest.raises(cfg.UnknownProfileError, match="unknown profile"):
        cfg.load_profile("missing", root)


# --- load_config integration ----------------------------------------------------


def test_bare_load_uses_packaged_defaults_only() -> None:
    resolved = cfg.load_config(env={})
    assert resolved.config.root_seed == 42
    assert [layer.name for layer in resolved.provenance.layers] == ["packaged-defaults"]


def test_load_with_root_reads_default_yaml(tmp_path: Path) -> None:
    root = _make_root(tmp_path)
    resolved = cfg.load_config(root, env={})
    names = [layer.name for layer in resolved.provenance.layers]
    assert names == ["packaged-defaults", "configs/default.yaml"]


def test_load_without_default_yaml_skips_that_layer(tmp_path: Path) -> None:
    root = _make_root(tmp_path, with_default=False)
    resolved = cfg.load_config(root, env={})
    assert [layer.name for layer in resolved.provenance.layers] == ["packaged-defaults"]


def test_load_with_profile_and_overrides(tmp_path: Path) -> None:
    root = _make_root(tmp_path)
    resolved = cfg.load_config(
        root,
        profile="ci",
        env={"SAB_LIMITS__WALL_CLOCK_S": "45"},
        cli_overrides={"jobs": 4},
        dataset_overrides={"limits.memory_mb": 1024},
    )
    config = resolved.config
    assert config.jobs == 4  # cli beats profile's jobs: 2
    assert config.log_level == "WARNING"  # profile
    assert config.limits.wall_clock_s == 45  # environment
    assert config.limits.memory_mb == 1024  # per-dataset override
    assert [layer.kind for layer in resolved.provenance.layers] == [
        "packaged",
        "default",
        "profile",
        "environment",
        "cli",
        "dataset",
    ]


def test_profile_without_root_raises() -> None:
    with pytest.raises(cfg.ConfigError, match="no config_root"):
        cfg.load_config(profile="ci", env={})


def test_config_root_thresholds_override_package_data(tmp_path: Path) -> None:
    root = _make_root(tmp_path, with_thresholds=True)
    resolved = cfg.load_config(root, env={})
    assert resolved.config.thresholds["matching"]["tau_jaccard"] == 0.7
    assert resolved.provenance.threshold_source == str(root / "thresholds" / "STO-1.0.0.yaml")


def test_load_reads_process_environment_when_env_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAB_ROOT_SEED", "13")
    resolved = cfg.load_config()
    assert resolved.config.root_seed == 13
    assert resolved.provenance.env_overrides == {"root_seed": 13}


def test_pin_override_through_load_config(tmp_path: Path) -> None:
    root = _make_root(tmp_path)
    resolved = cfg.load_config(
        root, cli_overrides={"pins.bench_version": "1.5.0"}, allow_pin_override=True, env={}
    )
    assert resolved.config.pins.bench_version == "1.5.0"
    assert resolved.provenance.pin_overrides[0].new == "1.5.0"


def test_load_config_is_deterministic(tmp_path: Path) -> None:
    root = _make_root(tmp_path)
    first = cfg.load_config(root, profile="ci", env={})
    second = cfg.load_config(root, profile="ci", env={})
    assert first.config_hash() == second.config_hash()
    assert first.to_mapping() == second.to_mapping()

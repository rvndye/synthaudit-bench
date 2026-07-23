"""Unit tests for configuration resolution: precedence, provenance, pins, hashing."""

from __future__ import annotations

from typing import Any

import pytest

from synthaudit_bench import config as cfg
from synthaudit_bench.model.config import Config


def _thresholds(sto_version: str) -> tuple[dict[str, Any], str]:
    return {"sto_version": sto_version, "matching": {"tau_jaccard": 0.5}}, "test-thresholds"


def _base() -> cfg.ConfigLayer:
    return cfg.ConfigLayer(
        name="packaged-defaults", data=cfg.packaged_defaults(), kind="packaged", is_base=True
    )


def _resolve(
    *override_layers: cfg.ConfigLayer, allow_pin_override: bool = False
) -> cfg.ResolvedConfig:
    return cfg.resolve_config(
        [_base(), *override_layers],
        thresholds_loader=_thresholds,
        allow_pin_override=allow_pin_override,
    )


# --- default loading ------------------------------------------------------------


def test_defaults_resolve_to_valid_config() -> None:
    resolved = _resolve()
    assert isinstance(resolved.config, Config)
    assert resolved.config.root_seed == 42
    assert resolved.config.pins.bench_version == "1.0.0"
    assert resolved.config.thresholds["matching"]["tau_jaccard"] == 0.5
    assert resolved.provenance.layers[0].name == "packaged-defaults"


# --- layered overrides and precedence ------------------------------------------


def test_higher_layer_wins_for_scalar() -> None:
    a = cfg.ConfigLayer("a", {"root_seed": 1}, kind="cli")
    b = cfg.ConfigLayer("b", {"root_seed": 2}, kind="dataset")
    assert _resolve(a, b).config.root_seed == 2


def test_deep_merge_preserves_untouched_siblings() -> None:
    override = cfg.ConfigLayer("env", {"limits": {"wall_clock_s": 5}}, kind="environment")
    resolved = _resolve(override)
    assert resolved.config.limits.wall_clock_s == 5
    assert resolved.config.limits.memory_mb == 8192  # untouched sibling from defaults


def test_precedence_chain_end_to_end() -> None:
    profile = cfg.ConfigLayer("profiles/ci", {"limits": {"wall_clock_s": 100}}, kind="profile")
    env = cfg.ConfigLayer("environment", {"limits": {"wall_clock_s": 45}}, kind="environment")
    cli = cfg.ConfigLayer("cli", {"jobs": 4}, kind="cli")
    resolved = _resolve(profile, env, cli)
    assert resolved.config.limits.wall_clock_s == 45  # env beats profile
    assert resolved.config.jobs == 4


# --- provenance -----------------------------------------------------------------


def test_provenance_tracks_source_of_each_value() -> None:
    env = cfg.ConfigLayer("environment", {"root_seed": 7}, kind="environment")
    resolved = _resolve(env)
    prov = resolved.provenance
    assert prov.sources["root_seed"] == "environment"
    assert prov.sources["pins.bench_version"] == "packaged-defaults"
    assert "root_seed" in prov.overridden  # set by defaults then environment
    assert prov.env_overrides == {"root_seed": 7}


def test_provenance_layer_contributions_list_owned_keys() -> None:
    cli = cfg.ConfigLayer("cli", {"jobs": 4}, kind="cli", source="cli")
    resolved = _resolve(cli)
    contribs = {c.name: c for c in cfg.configuration_layers(resolved)}
    assert contribs["cli"].keys == ("jobs",)
    assert "jobs" not in contribs["packaged-defaults"].keys
    assert resolved.to_mapping()["provenance"]["profile"] is None


def test_provenance_records_profile_and_threshold_version() -> None:
    profile = cfg.ConfigLayer("profiles/ci", {"jobs": 2}, kind="profile")
    resolved = _resolve(profile)
    assert resolved.provenance.profile == "profiles/ci"
    assert resolved.provenance.threshold_version == "1.0.0"
    assert resolved.provenance.threshold_source == "test-thresholds"


# --- version pins ---------------------------------------------------------------


def test_override_layer_cannot_change_pins_without_flag() -> None:
    bad = cfg.ConfigLayer("cli", {"pins": {"sto_version": "2.0.0"}}, kind="cli")
    with pytest.raises(cfg.PinOverrideError, match="version pins"):
        _resolve(bad)


def test_pin_override_is_applied_and_recorded_with_flag() -> None:
    override = cfg.ConfigLayer("cli", {"pins": {"bench_version": "1.1.0"}}, kind="cli")
    resolved = _resolve(override, allow_pin_override=True)
    assert resolved.config.pins.bench_version == "1.1.0"
    events = resolved.provenance.pin_overrides
    assert len(events) == 1
    assert (events[0].path, events[0].previous, events[0].new, events[0].layer) == (
        "pins.bench_version",
        "1.0.0",
        "1.1.0",
        "cli",
    )


def test_base_layer_may_set_pins() -> None:
    base_override = cfg.ConfigLayer(
        "configs/default.yaml", {"pins": {"bench_version": "1.2.0"}}, kind="default", is_base=True
    )
    assert _resolve(base_override).config.pins.bench_version == "1.2.0"


# --- configuration hash ---------------------------------------------------------


def test_config_hash_is_reproducible_and_content_addressed() -> None:
    assert _resolve().config_hash() == _resolve().config_hash()
    assert cfg.config_hash(_resolve()) == _resolve().config.content_hash()
    changed = _resolve(cfg.ConfigLayer("cli", {"root_seed": 9}, kind="cli"))
    assert changed.config_hash() != _resolve().config_hash()


def test_threshold_change_changes_the_hash() -> None:
    a = cfg.resolve_config([_base()], thresholds_loader=lambda v: ({"sto_version": v, "x": 1}, "s"))
    b = cfg.resolve_config([_base()], thresholds_loader=lambda v: ({"sto_version": v, "x": 2}, "s"))
    assert a.config_hash() != b.config_hash()


def test_config_hash_rejects_other_types() -> None:
    with pytest.raises(TypeError, match="cannot hash"):
        cfg.config_hash("not a config")  # type: ignore[arg-type]


def test_effective_configuration_returns_the_config() -> None:
    resolved = _resolve()
    assert cfg.effective_configuration(resolved) is resolved.config


# --- invalid configurations -----------------------------------------------------


def test_unknown_key_fails_closed() -> None:
    bad = cfg.ConfigLayer("cli", {"bogus": 1}, kind="cli")
    with pytest.raises(cfg.ConfigError, match="invalid"):
        _resolve(bad)


def test_type_error_fails_closed() -> None:
    bad = cfg.ConfigLayer("cli", {"root_seed": "not-an-int"}, kind="cli")
    with pytest.raises(cfg.ConfigError):
        _resolve(bad)


def test_missing_pins_raises() -> None:
    layer = cfg.ConfigLayer("only", {"root_seed": 1}, kind="packaged", is_base=True)
    with pytest.raises(cfg.ConfigError, match=r"pins\.sto_version"):
        cfg.resolve_config([layer], thresholds_loader=_thresholds)


def test_scalar_replaced_by_mapping_in_later_layer() -> None:
    # a base scalar becoming a mapping exercises the non-dict-existing merge branch
    a = cfg.ConfigLayer("a", {"limits": 5}, kind="packaged", is_base=True)
    b = cfg.ConfigLayer(
        "b", {"limits": {"wall_clock_s": 1, "memory_mb": 2}}, kind="default", is_base=True
    )
    merged = cfg.resolve_config([_base(), a, b], thresholds_loader=_thresholds)
    assert merged.config.limits.wall_clock_s == 1

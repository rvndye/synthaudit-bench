"""Unit tests for the resolved run configuration and its value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.config import Config, Pins, ResourceLimits


def _pins(**overrides: object) -> Pins:
    base: dict[str, object] = {"bench_version": "1.0.0", "sto_version": "1.0.0"}
    base.update(overrides)
    return Pins(**base)  # type: ignore[arg-type]


def test_resource_limits_omit_unset() -> None:
    assert ResourceLimits().to_mapping() == {}
    full = ResourceLimits(wall_clock_s=30.0, memory_mb=2048)
    assert ResourceLimits.from_mapping(full.to_mapping()) == full


def test_pins_round_trip_minimal_and_full() -> None:
    minimal = _pins()
    assert minimal.to_mapping() == {
        "bench_version": "1.0.0",
        "sto_version": "1.0.0",
        "schema_versions": {},
    }
    assert Pins.from_mapping(minimal.to_mapping()) == minimal
    full = _pins(
        schema_versions={"dataset": "1.0", "tuple": "1.0"},
        synthaudit_version="0.9.0",
        thresholds_ref="configs/thresholds/STO-1.0.0.yaml",
    )
    assert Pins.from_mapping(full.to_mapping()) == full
    assert full.to_mapping()["schema_versions"] == {"dataset": "1.0", "tuple": "1.0"}


def test_config_defaults_and_round_trip() -> None:
    config = Config(pins=_pins())
    assert config.root_seed == 42
    assert config.allow_pin_override is False
    assert Config.from_mapping(config.to_mapping()) == config


def test_config_full_round_trip() -> None:
    config = Config(
        pins=_pins(synthaudit_version="0.9.0"),
        root_seed=7,
        thresholds={"tau_jaccard": 0.5, "operating_points": {"STO-A01": 0.9}},
        limits=ResourceLimits(wall_clock_s=60.0, memory_mb=4096),
        layers=("packaged", "default.yaml", "cli"),
        jobs=8,
        log_level="INFO",
        allow_pin_override=True,
    )
    assert Config.from_mapping(config.to_mapping()) == config
    assert config.to_mapping()["layers"] == ["packaged", "default.yaml", "cli"]


def test_config_hash_is_content_addressed_and_stable() -> None:
    a = Config(pins=_pins(), root_seed=1)
    b = Config(pins=_pins(), root_seed=2)
    assert a.content_hash() != b.content_hash()
    # Threshold key order must not change the hash (canonical serialization).
    c1 = Config(pins=_pins(), thresholds={"a": 1, "b": 2})
    c2 = Config(pins=_pins(), thresholds={"b": 2, "a": 1})
    assert c1.content_hash() == c2.content_hash()
    assert len(a.content_hash()) == 64
    assert isinstance(a.to_canonical(), bytes)


def test_config_is_immutable() -> None:
    config = Config(pins=_pins())
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.root_seed = 99  # type: ignore[misc]

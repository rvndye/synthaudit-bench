"""Layered configuration resolution: merge, pin enforcement, validation, hashing.

The resolver merges an ordered sequence of configuration layers under the fixed
precedence chain (packaged defaults < ``configs/default.yaml`` < profile <
environment < CLI < per-dataset overrides), enforces version-pin immutability,
loads the pinned thresholds, validates the result against the normative config
schema (failing closed), and produces an immutable :class:`ResolvedConfig` with
complete provenance and a reproducible configuration hash. Resolution never
depends on file-discovery order: the precedence is the declared layer order.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.config.errors import ConfigError, PinOverrideError
from synthaudit_bench.config.loader import (
    expand_dotted,
    load_profile,
    packaged_defaults,
    parse_env,
    read_yaml_file,
    resolve_thresholds,
)
from synthaudit_bench.config.provenance import (
    LayerContribution,
    PinOverride,
    Provenance,
    ResolvedConfig,
)
from synthaudit_bench.model.config import Config
from synthaudit_bench.schemas.errors import SchemaValidationError

__all__ = [
    "ConfigLayer",
    "config_hash",
    "configuration_layers",
    "effective_configuration",
    "load_config",
    "resolve_config",
]

_PINS = "pins"


@dataclass(frozen=True, slots=True)
class ConfigLayer:
    """One ordered configuration layer supplied to the resolver."""

    name: str
    data: Mapping[str, Any] = field(default_factory=dict)
    kind: str = "override"
    is_base: bool = False
    source: str | None = None


def _leaf_paths(mapping: Mapping[str, Any], prefix: str = "") -> Iterator[str]:
    for key, value in mapping.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping) and value:
            yield from _leaf_paths(value, path)
        else:
            yield path


def _get_path(mapping: Mapping[str, Any], path: str) -> Any:
    cursor: Any = mapping
    for segment in path.split("."):
        if isinstance(cursor, Mapping) and segment in cursor:
            cursor = cursor[segment]
        else:
            return None
    return cursor


def _merge_into(
    acc: dict[str, Any],
    data: Mapping[str, Any],
    prefix: str,
    layer_name: str,
    sources: dict[str, str],
    overridden: set[str],
) -> None:
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping) and value:
            existing = acc.get(key)
            if not isinstance(existing, dict):
                acc[key] = {}
            _merge_into(acc[key], value, path, layer_name, sources, overridden)
        else:
            if path in sources:
                overridden.add(path)
            sources[path] = layer_name
            acc[key] = copy.deepcopy(value)


def _pinned_paths(data: Mapping[str, Any]) -> list[str]:
    return [p for p in _leaf_paths(data) if p == _PINS or p.startswith(_PINS + ".")]


def _deep_merge(
    layers: Sequence[ConfigLayer], allow_pin_override: bool
) -> tuple[dict[str, Any], dict[str, str], set[str], list[PinOverride]]:
    acc: dict[str, Any] = {}
    sources: dict[str, str] = {}
    overridden: set[str] = set()
    pin_overrides: list[PinOverride] = []
    for layer in layers:
        if not layer.is_base:
            pinned = _pinned_paths(layer.data)
            if pinned:
                if not allow_pin_override:
                    raise PinOverrideError(
                        f"layer {layer.name!r} attempts to change version pins "
                        f"{sorted(pinned)} without allow_pin_override"
                    )
                for path in sorted(pinned):
                    pin_overrides.append(
                        PinOverride(
                            path=path,
                            previous=_get_path(acc, path),
                            new=_get_path(layer.data, path),
                            layer=layer.name,
                        )
                    )
        _merge_into(acc, layer.data, "", layer.name, sources, overridden)
    return acc, sources, overridden, pin_overrides


def _kind_data(layers: Sequence[ConfigLayer], kind: str) -> Mapping[str, Any]:
    for layer in layers:
        if layer.kind == kind:
            return layer.data
    return {}


def _build_provenance(
    layers: Sequence[ConfigLayer],
    sources: Mapping[str, str],
    overridden: set[str],
    pin_overrides: list[PinOverride],
    threshold_version: str,
    threshold_source: str,
) -> Provenance:
    contributions = tuple(
        LayerContribution(
            name=layer.name,
            source=layer.source,
            kind=layer.kind,
            keys=tuple(sorted(p for p, owner in sources.items() if owner == layer.name)),
        )
        for layer in layers
    )
    profile = next((layer.name for layer in layers if layer.kind == "profile"), None)
    return Provenance(
        layers=contributions,
        sources=MappingProxyType(dict(sources)),
        overridden=tuple(sorted(overridden)),
        profile=profile,
        threshold_version=threshold_version,
        threshold_source=threshold_source,
        env_overrides=MappingProxyType(copy.deepcopy(dict(_kind_data(layers, "environment")))),
        cli_overrides=MappingProxyType(copy.deepcopy(dict(_kind_data(layers, "cli")))),
        dataset_overrides=MappingProxyType(copy.deepcopy(dict(_kind_data(layers, "dataset")))),
        pin_overrides=tuple(pin_overrides),
    )


def resolve_config(
    layers: Iterable[ConfigLayer],
    *,
    thresholds_loader: Callable[[str], tuple[dict[str, Any], str]] | None = None,
    allow_pin_override: bool = False,
) -> ResolvedConfig:
    """Resolve an ordered sequence of layers into an immutable :class:`ResolvedConfig`.

    Layers are ordered lowest to highest precedence. Non-base layers may not
    change version pins unless ``allow_pin_override`` is set, in which case each
    change is recorded in provenance. Thresholds for the resolved STO version are
    loaded (from ``thresholds_loader`` if given, else the packaged operating
    points), the result is validated against the normative config schema, and the
    effective :class:`Config` and its provenance are returned.

    Raises:
        PinOverrideError: if a non-base layer changes a pin without the override.
        ConfigError: if pins are missing, thresholds are unavailable, or the
            resolved configuration fails schema validation.
    """
    layer_list = list(layers)
    merged, sources, overridden, pin_overrides = _deep_merge(layer_list, allow_pin_override)

    pins = merged.get(_PINS)
    if not isinstance(pins, Mapping) or "sto_version" not in pins:
        raise ConfigError("resolved configuration has no pins.sto_version")
    sto_version = str(pins["sto_version"])

    loader = thresholds_loader if thresholds_loader is not None else _packaged_thresholds
    thresholds, threshold_source = loader(sto_version)
    threshold_version = str(thresholds.get("sto_version", sto_version))

    merged["thresholds"] = thresholds
    merged["layers"] = [layer.name for layer in layer_list if layer.data]
    merged["allow_pin_override"] = allow_pin_override

    try:
        schemas.validate_instance("config", merged)
    except SchemaValidationError as exc:
        raise ConfigError(f"resolved configuration is invalid: {exc}") from exc

    config = Config.from_mapping(merged)
    provenance = _build_provenance(
        layer_list, sources, overridden, pin_overrides, threshold_version, threshold_source
    )
    return ResolvedConfig(config=config, provenance=provenance)


def _packaged_thresholds(sto_version: str) -> tuple[dict[str, Any], str]:
    return resolve_thresholds(sto_version, None)


def load_config(
    config_root: str | Path | None = None,
    *,
    profile: str | None = None,
    env: Mapping[str, str] | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
    dataset_overrides: Mapping[str, Any] | None = None,
    allow_pin_override: bool = False,
) -> ResolvedConfig:
    """Load and resolve the full configuration layer stack.

    Assembles the layers in precedence order: packaged defaults, then
    ``<config_root>/default.yaml`` if present, then the named profile, then the
    ``SAB_*`` environment overrides (from ``env`` or the process environment),
    then CLI overrides, then per-dataset overrides. Thresholds are read from
    ``config_root`` if it overrides them, else from package data.

    Raises:
        ConfigError: if a profile is requested without a config root, or the
            resolved configuration is invalid.
        UnknownProfileError: if the named profile does not exist.
        PinOverrideError: if an override layer changes a pin without the override.
    """
    root = Path(config_root) if config_root is not None else None
    layers: list[ConfigLayer] = [
        ConfigLayer(
            name="packaged-defaults",
            data=packaged_defaults(),
            kind="packaged",
            is_base=True,
            source="packaged",
        )
    ]

    if root is not None:
        default_path = root / "default.yaml"
        if default_path.is_file():
            layers.append(
                ConfigLayer(
                    name="configs/default.yaml",
                    data=read_yaml_file(default_path),
                    kind="default",
                    is_base=True,
                    source=str(default_path),
                )
            )

    if profile is not None:
        if root is None:
            raise ConfigError("a profile was requested but no config_root was given")
        layers.append(
            ConfigLayer(
                name=f"profiles/{profile}",
                data=load_profile(profile, root),
                kind="profile",
                source=str(root / "profiles" / f"{profile}.yaml"),
            )
        )

    environ = env if env is not None else dict(os.environ)
    env_data = parse_env(environ)
    if env_data:
        layers.append(
            ConfigLayer(name="environment", data=env_data, kind="environment", source="environment")
        )

    if cli_overrides:
        layers.append(
            ConfigLayer(name="cli", data=expand_dotted(cli_overrides), kind="cli", source="cli")
        )

    if dataset_overrides:
        layers.append(
            ConfigLayer(
                name="dataset",
                data=expand_dotted(dataset_overrides),
                kind="dataset",
                source="dataset",
            )
        )

    def _loader(sto_version: str) -> tuple[dict[str, Any], str]:
        return resolve_thresholds(sto_version, root)

    return resolve_config(layers, thresholds_loader=_loader, allow_pin_override=allow_pin_override)


def config_hash(config: ResolvedConfig | Config) -> str:
    """Return the configuration hash of a resolved configuration or a ``Config``."""
    if isinstance(config, ResolvedConfig):
        return config.config.content_hash()
    if isinstance(config, Config):
        return config.content_hash()
    raise TypeError(f"cannot hash {type(config).__name__} as a configuration")


def configuration_layers(resolved: ResolvedConfig) -> tuple[LayerContribution, ...]:
    """Return the ordered layer provenance of a resolved configuration."""
    return resolved.provenance.layers


def effective_configuration(resolved: ResolvedConfig) -> Config:
    """Return the effective :class:`Config` (the resolved values)."""
    return resolved.config

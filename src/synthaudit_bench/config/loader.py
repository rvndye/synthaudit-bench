"""Reading configuration sources: packaged defaults, files, profiles, thresholds, env.

Every function here is deterministic and side-effect-free beyond reading a
configuration file or an injected environment mapping. YAML is parsed with the
safe loader; a source that is not a mapping is rejected. Environment values are
parsed as YAML scalars so ``SAB_ROOT_SEED=7`` yields the integer 7.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from synthaudit_bench.config.errors import ConfigError, UnknownProfileError

__all__ = ["expand_dotted", "load_profile", "load_thresholds", "packaged_defaults", "parse_env"]

_PACKAGE = "synthaudit_bench"

# The packaged-default baseline: the lowest configuration layer, complete enough
# that a bare load with no files, environment, or overrides yields a valid,
# schema-conformant configuration from an installed wheel.
_DEFAULTS: dict[str, Any] = {
    "pins": {
        "bench_version": "1.0.0",
        "sto_version": "1.0.0",
        "synthaudit_version": "0.1.0",
        "thresholds_ref": "STO-1.0.0",
        "schema_versions": {
            "dataset": "1.0.0",
            "artifact-tuple": "1.0.0",
            "gold-tuple": "1.0.0",
            "report-card": "1.0.0",
            "run-manifest": "1.0.0",
            "metrics": "1.0.0",
            "config": "1.0.0",
        },
    },
    "root_seed": 42,
    "limits": {"wall_clock_s": 1800, "memory_mb": 8192},
    "log_level": "INFO",
}


def packaged_defaults() -> dict[str, Any]:
    """Return a fresh deep copy of the packaged-default configuration baseline."""
    return copy.deepcopy(_DEFAULTS)


def _as_mapping(loaded: Any, source: str) -> dict[str, Any]:
    if loaded is None:
        return {}
    if not isinstance(loaded, Mapping):
        raise ConfigError(f"configuration source {source!r} is not a mapping")
    return dict(loaded)


def read_yaml_file(path: Path) -> dict[str, Any]:
    """Read and parse a YAML configuration file into a mapping."""
    if not path.is_file():
        raise ConfigError(f"configuration file not found: {path}")
    return _as_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))


def load_profile(name: str, config_root: Path) -> dict[str, Any]:
    """Load the profile ``name`` from ``<config_root>/profiles/<name>.yaml``."""
    path = config_root / "profiles" / f"{name}.yaml"
    if not path.is_file():
        raise UnknownProfileError(f"unknown profile {name!r} (looked for {path})")
    return read_yaml_file(path)


def resolve_thresholds(
    sto_version: str, config_root: Path | None = None
) -> tuple[dict[str, Any], str]:
    """Return the thresholds mapping for ``sto_version`` and its source label.

    A ``<config_root>/thresholds/STO-<version>.yaml`` file takes precedence; when
    absent, the operating points shipped as package data are used.
    """
    filename = f"STO-{sto_version}.yaml"
    if config_root is not None:
        candidate = config_root / "thresholds" / filename
        if candidate.is_file():
            return read_yaml_file(candidate), str(candidate)
    resource = resources.files(_PACKAGE) / "config_data" / "thresholds" / filename
    if resource.is_file():
        text = resource.read_text(encoding="utf-8")
        return _as_mapping(yaml.safe_load(text), f"packaged:{filename}"), (
            f"packaged:config_data/thresholds/{filename}"
        )
    raise ConfigError(f"no thresholds available for STO version {sto_version!r}")


def load_thresholds(sto_version: str, config_root: Path | None = None) -> dict[str, Any]:
    """Return the thresholds mapping for ``sto_version`` (detector operating points)."""
    return resolve_thresholds(sto_version, config_root)[0]


def _set_path(target: dict[str, Any], path: list[str], value: Any) -> None:
    cursor = target
    for segment in path[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    cursor[path[-1]] = value


def parse_env(environ: Mapping[str, str], prefix: str = "SAB_") -> dict[str, Any]:
    """Parse ``SAB_*`` environment variables into a nested override mapping.

    Keys are read in sorted order for determinism; ``__`` separates nesting
    levels (``SAB_LIMITS__WALL_CLOCK_S``) and the remainder keeps its single
    underscores (``SAB_ROOT_SEED`` -> ``root_seed``). Each value is parsed as a
    YAML scalar, so numbers and booleans are typed rather than left as strings.
    """
    result: dict[str, Any] = {}
    for key in sorted(environ):
        if not key.startswith(prefix):
            continue
        path = [segment.lower() for segment in key[len(prefix) :].split("__")]
        _set_path(result, path, yaml.safe_load(environ[key]))
    return result


def expand_dotted(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Expand dotted keys into nested mappings (``{"a.b": 1}`` -> ``{"a": {"b": 1}}``)."""
    result: dict[str, Any] = {}
    for key, value in mapping.items():
        expanded = expand_dotted(value) if isinstance(value, Mapping) else value
        if isinstance(key, str) and "." in key:
            _set_path(result, key.split("."), expanded)
        else:
            result[key] = expanded
    return result

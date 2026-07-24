"""Detector registration and entry-point discovery (the plugin mechanism).

Detectors extend the benchmark without any core edit, through the
``synthaudit_bench.detectors`` entry-point group (architecture Section 9). This
module discovers them and lets a caller register detectors programmatically.

A :class:`DetectorRegistry` is an immutable value: registration and discovery
return a new registry rather than mutating shared state, so there is no mutable
global anywhere. Discovery is lazy and isolation-safe: each entry point is loaded
independently, and one that fails to import is recorded and skipped, never
breaking the others (architecture Section 9, "a plugin that fails to import is
logged and skipped, not fatal").
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib.metadata import entry_points
from types import MappingProxyType
from typing import Any, Protocol

from synthaudit_bench.detector.base import Detector
from synthaudit_bench.detector.errors import RegistrationError, UnknownDetectorError

__all__ = [
    "DETECTOR_ENTRY_POINT_GROUP",
    "DetectorFactory",
    "DetectorRegistry",
    "discover_detectors",
    "register_detector",
]

DETECTOR_ENTRY_POINT_GROUP = "synthaudit_bench.detectors"
"""The entry-point group third-party detectors declare (architecture Section 9)."""

DetectorFactory = Callable[[], Detector]
"""A zero-argument callable that constructs a fresh :class:`Detector`."""


class _EntryPoint(Protocol):
    name: str

    def load(self) -> Any: ...  # pragma: no cover - protocol stub


@dataclass(frozen=True, slots=True)
class DetectorRegistry:
    """An immutable name-to-factory registry with recorded discovery errors."""

    factories: MappingProxyType[str, DetectorFactory]
    import_errors: MappingProxyType[str, str]

    def names(self) -> tuple[str, ...]:
        """Return the registered detector names, sorted."""
        return tuple(sorted(self.factories))

    def contains(self, name: str) -> bool:
        """Return whether ``name`` is registered."""
        return name in self.factories

    def factory(self, name: str) -> DetectorFactory:
        """Return the factory registered under ``name``.

        Raises:
            UnknownDetectorError: if ``name`` is not registered.
        """
        try:
            return self.factories[name]
        except KeyError:
            raise UnknownDetectorError(f"no detector registered as {name!r}") from None

    def create(self, name: str) -> Detector:
        """Construct the detector registered under ``name`` (lazy instantiation).

        Raises:
            UnknownDetectorError: if ``name`` is not registered.
        """
        return self.factory(name)()

    def with_detector(
        self, name: str, factory: DetectorFactory, *, replace: bool = False
    ) -> DetectorRegistry:
        """Return a new registry with ``name`` added (or replaced).

        Raises:
            RegistrationError: if ``name`` is already registered and ``replace``
                is false.
        """
        if name in self.factories and not replace:
            raise RegistrationError(f"detector {name!r} is already registered")
        merged = dict(self.factories)
        merged[name] = factory
        return DetectorRegistry(MappingProxyType(merged), self.import_errors)

    def with_error(self, name: str, detail: str) -> DetectorRegistry:
        """Return a new registry recording that discovering ``name`` failed."""
        merged = dict(self.import_errors)
        merged[name] = detail
        return DetectorRegistry(self.factories, MappingProxyType(merged))

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive summary of this registry."""
        return {
            "detectors": self.names(),
            "import_errors": {k: self.import_errors[k] for k in sorted(self.import_errors)},
        }


def _empty() -> DetectorRegistry:
    return DetectorRegistry(MappingProxyType({}), MappingProxyType({}))


def register_detector(
    name: str,
    factory: DetectorFactory,
    *,
    registry: DetectorRegistry | None = None,
    replace: bool = False,
) -> DetectorRegistry:
    """Register ``factory`` under ``name``, returning a new registry.

    With no ``registry`` a fresh one is started. Registration is a pure value
    update: the input registry is never mutated (there is no shared global).

    Raises:
        RegistrationError: if ``name`` already exists and ``replace`` is false.
    """
    base = registry if registry is not None else _empty()
    return base.with_detector(name, factory, replace=replace)


def discover_detectors(
    *,
    group: str = DETECTOR_ENTRY_POINT_GROUP,
    registry: DetectorRegistry | None = None,
    entry_points_override: Iterable[_EntryPoint] | None = None,
) -> DetectorRegistry:
    """Discover detectors from the entry-point ``group``, returning a new registry.

    Each entry point is loaded independently and in deterministic (name) order; an
    entry point whose import fails is recorded in ``import_errors`` and skipped, so
    one broken or heavy optional plugin never affects the others. ``entry_points_override``
    injects a fixed set of entry points (used in testing) instead of the installed
    environment's.
    """
    base = registry if registry is not None else _empty()
    if entry_points_override is not None:
        points: Iterable[_EntryPoint] = entry_points_override
    else:
        points = entry_points(group=group)
    for point in sorted(points, key=lambda ep: ep.name):
        try:
            factory = point.load()
        except Exception as exc:  # isolation: a broken plugin is recorded, not fatal
            base = base.with_error(point.name, f"{type(exc).__name__}: {exc}")
            continue
        base = base.with_detector(point.name, factory, replace=True)
    return base

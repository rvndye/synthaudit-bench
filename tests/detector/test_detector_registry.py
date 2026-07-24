"""Unit tests for detector registration and entry-point discovery."""

from __future__ import annotations

from typing import Any

import pytest
from _dethelpers import FunctionDetector, caps, const_findings

from synthaudit_bench.detector import (
    DetectorRegistry,
    discover_detectors,
    register_detector,
)
from synthaudit_bench.detector.errors import RegistrationError, UnknownDetectorError


def _factory() -> FunctionDetector:
    return FunctionDetector(caps(name="demo"), const_findings)


class _FakeEP:
    def __init__(self, name: str, obj: Any, *, fail: bool = False) -> None:
        self.name = name
        self._obj = obj
        self._fail = fail

    def load(self) -> Any:
        if self._fail:
            raise ImportError(f"cannot import {self.name}")
        return self._obj


def test_register_starts_fresh_and_creates() -> None:
    reg = register_detector("demo", _factory)
    assert reg.names() == ("demo",)
    assert reg.contains("demo")
    detector = reg.create("demo")
    assert detector.capabilities().name == "demo"


def test_register_is_immutable_update() -> None:
    first = register_detector("a", _factory)
    second = register_detector("b", _factory, registry=first)
    assert first.names() == ("a",)  # the original is untouched
    assert second.names() == ("a", "b")


def test_register_duplicate_raises() -> None:
    reg = register_detector("demo", _factory)
    with pytest.raises(RegistrationError, match="already registered"):
        register_detector("demo", _factory, registry=reg)


def test_register_replace_allowed() -> None:
    reg = register_detector("demo", _factory)
    replaced = register_detector("demo", _factory, registry=reg, replace=True)
    assert replaced.names() == ("demo",)


def test_factory_unknown_raises() -> None:
    reg = register_detector("demo", _factory)
    with pytest.raises(UnknownDetectorError, match="no detector registered"):
        reg.factory("missing")
    with pytest.raises(UnknownDetectorError):
        reg.create("missing")


def test_registry_to_mapping() -> None:
    reg = register_detector("demo", _factory).with_error("broken", "ImportError: x")
    mapping = reg.to_mapping()
    assert mapping["detectors"] == ("demo",)
    assert mapping["import_errors"] == {"broken": "ImportError: x"}


def test_discover_from_injected_entry_points_isolates_failures() -> None:
    points = [_FakeEP("good", _factory), _FakeEP("bad", None, fail=True)]
    reg = discover_detectors(entry_points_override=points)
    assert reg.names() == ("good",)
    assert "bad" in reg.import_errors
    assert reg.import_errors["bad"].startswith("ImportError")


def test_discover_merges_into_base_registry() -> None:
    base = register_detector("pre", _factory)
    reg = discover_detectors(entry_points_override=[_FakeEP("post", _factory)], registry=base)
    assert reg.names() == ("post", "pre")


def test_discover_default_group_reads_environment() -> None:
    # No detectors are installed in this environment, so the real lookup is empty.
    reg = discover_detectors()
    assert isinstance(reg, DetectorRegistry)
    assert reg.names() == ()

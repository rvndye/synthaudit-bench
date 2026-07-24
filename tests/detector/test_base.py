"""Unit tests for the detector protocol, capability model, and execution context."""

from __future__ import annotations

import pytest
from _dethelpers import FunctionDetector, MinimalDetector, caps, const_findings

from synthaudit_bench.detector import (
    BaseDetector,
    Detector,
    DetectorMetadata,
    ExecutionContext,
    RawFinding,
    capability_issues,
    detector_capabilities,
    detector_metadata,
    version_compatible,
)
from synthaudit_bench.detector.base import CapabilityIssue, DetectionResult


def test_execution_context_to_mapping_minimal() -> None:
    ctx = ExecutionContext()
    mapping = ctx.to_mapping()
    assert mapping == {
        "seed": 42,
        "bench_version": "1.0.0",
        "sto_version": "1.0.0",
        "thresholds": {},
    }


def test_execution_context_to_mapping_full() -> None:
    ctx = ExecutionContext(seed=7, thresholds={"tau": 0.9}, timeout_s=1.5, config_hash="abc")
    mapping = ctx.to_mapping()
    assert mapping["timeout_s"] == 1.5
    assert mapping["config_hash"] == "abc"
    assert mapping["thresholds"] == {"tau": 0.9}


def test_raw_finding_defaults() -> None:
    finding = RawFinding(identifier="STO-S02", support=("a",))
    assert finding.disposition is None
    assert finding.confidence_kind == "native"


def test_detection_result_defaults() -> None:
    result = DetectionResult()
    assert result.findings == ()
    assert result.partial is False


def test_capabilities_implementation_name_default_and_explicit() -> None:
    assert caps().implementation_name == "test"
    assert caps(implementation="impl").implementation_name == "impl"


@pytest.mark.parametrize(
    "modalities,modality,expected",
    [
        (frozenset(), "tabular", True),
        (frozenset({"tabular"}), "tabular", True),
        (frozenset({"image"}), "tabular", False),
    ],
)
def test_supports_modality(modalities: frozenset[str], modality: str, expected: bool) -> None:
    assert caps(modalities=modalities).supports_modality(modality) is expected


@pytest.mark.parametrize(
    "types,logical,expected",
    [
        (frozenset(), "numeric", True),
        (frozenset({"numeric"}), "numeric", True),
        (frozenset({"numeric"}), "datetime", False),
    ],
)
def test_supports_logical_type(types: frozenset[str], logical: str, expected: bool) -> None:
    assert caps(logical_types=types).supports_logical_type(logical) is expected


def test_supports_class_by_group_and_exact_and_open() -> None:
    assert caps().supports_class("STO-A07") is True  # empty categories accept all
    by_group = caps(sto_categories=frozenset({"A"}))
    assert by_group.supports_class("STO-A07") is True
    assert by_group.supports_class("STO-S02") is False
    exact = caps(sto_categories=frozenset({"STO-A07"}))
    assert exact.supports_class("STO-A07") is True
    assert exact.supports_class("STO-A01") is False
    assert exact.supports_class("ABSTAIN") is False  # non-STO prefix -> empty group


def test_capabilities_to_mapping_variants() -> None:
    minimal = caps().to_mapping()
    assert "required_sto_version" not in minimal and "probe_family" not in minimal
    full = caps(required_sto_version="1.0.0", probe_family="trees").to_mapping()
    assert full["required_sto_version"] == "1.0.0"
    assert full["probe_family"] == "trees"


def test_detector_capabilities_and_metadata() -> None:
    detector = FunctionDetector(caps(sto_categories=frozenset({"S"})), const_findings)
    assert detector_capabilities(detector).name == "test"
    meta = detector_metadata(detector)
    assert isinstance(meta, DetectorMetadata)
    assert meta.required_bench_version == "1.0.0"
    assert "required_sto_version" not in meta.to_mapping()


def test_detector_metadata_with_sto_requirement() -> None:
    detector = MinimalDetector(caps(required_sto_version="1.0.0"), const_findings)
    assert detector_metadata(detector).to_mapping()["required_sto_version"] == "1.0.0"


def test_base_detector_lifecycle_noops() -> None:
    base = BaseDetector()
    base.setup(ExecutionContext())  # no-op lifecycle hooks
    base.teardown()


def test_detector_protocol_runtime_checkable() -> None:
    assert isinstance(FunctionDetector(caps(), const_findings), Detector)
    assert not isinstance(object(), Detector)


@pytest.mark.parametrize(
    "available,required,expected",
    [
        ("1.2.0", "1.0.0", True),
        ("1.0.0", "1.2.0", False),
        ("2.0.0", "1.0.0", False),
        ("bad", "1.0.0", False),
        ("1.0.0", "bad", False),
    ],
)
def test_version_compatible(available: str, required: str, expected: bool) -> None:
    assert version_compatible(available, required) is expected


def test_capability_issues_none_when_compatible() -> None:
    assert capability_issues(caps(), ExecutionContext()) == ()


def test_capability_issues_bench_version() -> None:
    issues = capability_issues(caps(required_bench_version="2.0.0"), ExecutionContext())
    assert issues[0].code == "unsupported_version"
    assert isinstance(issues[0], CapabilityIssue)


def test_capability_issues_sto_version() -> None:
    issues = capability_issues(
        caps(required_sto_version="2.0.0"), ExecutionContext(sto_version="1.0.0")
    )
    assert any("ontology" in i.detail for i in issues)


def test_capability_issues_modality_and_types() -> None:
    caps_obj = caps(modalities=frozenset({"tabular"}), logical_types=frozenset({"numeric"}))
    issues = capability_issues(
        caps_obj, ExecutionContext(), modality="image", logical_types=frozenset({"datetime"})
    )
    codes = {i.code for i in issues}
    assert codes == {"unsupported_capability"}
    assert len(issues) == 2

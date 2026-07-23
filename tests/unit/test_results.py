"""Unit tests for the audit result and its value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord
from synthaudit_bench.model.tuples import ROWS, ArtifactTuple

_DET = DetectorInfo(name="synthaudit", version="0.1.0", probe_family="gbm")
_A1 = ArtifactTuple(support=frozenset({"a"}), sto_class="STO-A01")
_A2 = ArtifactTuple(support=ROWS, sto_class="STO-S01")


def test_detector_round_trip() -> None:
    assert DetectorInfo.from_mapping(_DET.to_mapping()) == _DET
    plain = DetectorInfo(name="x", version="1", capabilities=("linear",))
    assert DetectorInfo.from_mapping(plain.to_mapping()) == plain


def test_error_round_trip() -> None:
    err = ErrorRecord(code="ingest", detail="unparseable")
    assert ErrorRecord.from_mapping(err.to_mapping()) == err


def test_audit_result_round_trip_and_sorting() -> None:
    result = AuditResult(
        dataset_id="grid",
        dataset_sha256="h" * 64,
        detector=_DET,
        tuples=(_A2, _A1),  # deliberately unsorted
        notes=("ok",),
        runtime_s=1.5,
    )
    assert result.tuples == (_A1, _A2)  # normalized to sorted order
    assert AuditResult.from_mapping(result.to_mapping()) == result


def test_content_hash_excludes_runtime() -> None:
    common = {"dataset_id": "d", "dataset_sha256": "h", "detector": _DET, "tuples": (_A1,)}
    fast = AuditResult(**common, runtime_s=1.0)  # type: ignore[arg-type]
    slow = AuditResult(**common, runtime_s=99.0)  # type: ignore[arg-type]
    assert fast.content_hash() == slow.content_hash()
    assert fast.to_mapping()["runtime_s"] == 1.0
    assert isinstance(fast.to_canonical(), bytes)


def test_content_hash_is_content_addressed() -> None:
    a = AuditResult(dataset_id="d", dataset_sha256="h", detector=_DET, tuples=(_A1,))
    b = AuditResult(dataset_id="d", dataset_sha256="h", detector=_DET, tuples=(_A2,))
    assert a.content_hash() != b.content_hash()


def test_audit_result_with_error_round_trips() -> None:
    result = AuditResult(
        dataset_id="d",
        dataset_sha256="h",
        detector=_DET,
        error=ErrorRecord(code="resource", detail="timeout"),
    )
    restored = AuditResult.from_mapping(result.to_mapping())
    assert restored == result
    assert restored.error is not None
    assert restored.error.code == "resource"


def test_audit_result_is_immutable() -> None:
    result = AuditResult(dataset_id="d", dataset_sha256="h", detector=_DET)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.dataset_id = "x"  # type: ignore[misc]


def test_disposition_preserved_in_tuples() -> None:
    tup = ArtifactTuple(
        support=frozenset({"a", "b"}),
        sto_class="STO-A01",
        disposition=Disposition.STRUCTURAL_CONSTRAINT,
    )
    result = AuditResult(dataset_id="d", dataset_sha256="h", detector=_DET, tuples=(tup,))
    assert AuditResult.from_mapping(result.to_mapping()).tuples[0].disposition is (
        Disposition.STRUCTURAL_CONSTRAINT
    )

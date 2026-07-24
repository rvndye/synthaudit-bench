"""Unit tests for the raw-finding normalization pipeline."""

from __future__ import annotations

from typing import Any

import pytest
from _dethelpers import make_dataset

from synthaudit_bench import sto
from synthaudit_bench.detector import RawFinding, build_ontology_mapper, normalize_findings
from synthaudit_bench.detector.errors import ConfidenceError, InvalidFindingError
from synthaudit_bench.detector.normalize import (
    _canonical_support,
    _check_evidence,
    infer_disposition,
)
from synthaudit_bench.model.enums import Severity
from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.tuples import ROWS

_ONTO = sto.load()


# --------------------------------------------------------------------------- #
# canonical support                                                           #
# --------------------------------------------------------------------------- #


def test_canonical_support_token() -> None:
    assert _canonical_support(ROWS) == ROWS


def test_canonical_support_bad_string() -> None:
    with pytest.raises(InvalidFindingError, match="reserved token"):
        _canonical_support("column-name")


@pytest.mark.parametrize("value", [("a", "b"), ["a", "b"], {"a", "b"}, frozenset({"a", "b"})])
def test_canonical_support_collections(value: Any) -> None:
    assert _canonical_support(value) == frozenset({"a", "b"})


def test_canonical_support_empty() -> None:
    with pytest.raises(InvalidFindingError, match="non-empty"):
        _canonical_support(())


def test_canonical_support_non_collection() -> None:
    with pytest.raises(InvalidFindingError, match="token or a set"):
        _canonical_support(5)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# disposition inference                                                        #
# --------------------------------------------------------------------------- #


def test_infer_disposition_reserved_is_none() -> None:
    assert infer_disposition("STO-X00", frozenset({"a"}), "grade", _ONTO) is None


def test_infer_disposition_no_target() -> None:
    assert infer_disposition("STO-A01", frozenset({"a"}), None, _ONTO) is Disposition.NOT_APPLICABLE


def test_infer_disposition_target_independent_group_s() -> None:
    assert (
        infer_disposition("STO-S02", frozenset({"a"}), "grade", _ONTO) is Disposition.NOT_APPLICABLE
    )


def test_infer_disposition_target_independent_r02() -> None:
    assert infer_disposition("STO-R02", ROWS, "grade", _ONTO) is Disposition.NOT_APPLICABLE


def test_infer_disposition_token_target_relative_undecidable() -> None:
    assert infer_disposition("STO-R01", ROWS, "grade", _ONTO) is None


def test_infer_disposition_target_leakage() -> None:
    result = infer_disposition("STO-A01", frozenset({"grade", "x"}), "grade", _ONTO)
    assert result is Disposition.TARGET_LEAKAGE


def test_infer_disposition_redundancy_for_a08() -> None:
    assert (
        infer_disposition("STO-A08", frozenset({"b", "c"}), "grade", _ONTO)
        is Disposition.REDUNDANCY
    )


def test_infer_disposition_structural_constraint() -> None:
    result = infer_disposition("STO-A01", frozenset({"b", "c"}), "grade", _ONTO)
    assert result is Disposition.STRUCTURAL_CONSTRAINT


def test_infer_disposition_unknown_class_is_target_relative() -> None:
    result = infer_disposition("STO-Z99", frozenset({"b", "c"}), "grade", _ONTO)
    assert result is Disposition.STRUCTURAL_CONSTRAINT


# --------------------------------------------------------------------------- #
# evidence                                                                     #
# --------------------------------------------------------------------------- #


def test_check_evidence_variants() -> None:
    assert _check_evidence(None) is None
    assert _check_evidence("text") == "text"
    good = {"rule": "x>0", "count": 3, "nested": [1, 2], "ok": True}
    assert _check_evidence(good) == good


def test_check_evidence_bad_object() -> None:
    with pytest.raises(InvalidFindingError, match="JSON-primitive"):
        _check_evidence({"bad": {1, 2}})  # a set is not JSON-primitive


def test_check_evidence_wrong_type() -> None:
    with pytest.raises(InvalidFindingError, match="string or a JSON"):
        _check_evidence(42)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# full normalization                                                           #
# --------------------------------------------------------------------------- #


def test_normalize_maps_and_infers() -> None:
    ds = make_dataset()
    mapper = build_ontology_mapper({"dup": "STO-A08"})
    tuples = normalize_findings(
        [RawFinding("dup", ("b", "c")), RawFinding("STO-S02", ("const",))], ds, mapper=mapper
    )
    classes = [t.sto_class for t in tuples]
    assert classes == ["STO-A08", "STO-S02"]  # sorted deterministically
    assert tuples[0].disposition is Disposition.REDUNDANCY
    assert tuples[1].disposition is Disposition.NOT_APPLICABLE


def test_normalize_explicit_disposition_and_severity() -> None:
    ds = make_dataset()
    tuples = normalize_findings(
        [RawFinding("STO-A07", ("grade", "b"), disposition="target_leakage", severity="critical")],
        ds,
    )
    assert tuples[0].disposition is Disposition.TARGET_LEAKAGE
    assert tuples[0].severity is Severity.CRITICAL


def test_normalize_invalid_disposition() -> None:
    ds = make_dataset()
    with pytest.raises(InvalidFindingError, match="invalid disposition"):
        normalize_findings([RawFinding("STO-S02", ("const",), disposition="bogus")], ds)


def test_normalize_invalid_severity() -> None:
    ds = make_dataset()
    with pytest.raises(InvalidFindingError, match="invalid severity"):
        normalize_findings([RawFinding("STO-S02", ("const",), severity="huge")], ds)


def test_normalize_confidence_error_propagates() -> None:
    ds = make_dataset()
    with pytest.raises(ConfidenceError):
        normalize_findings([RawFinding("STO-S02", ("const",), confidence=2.0)], ds)


def test_normalize_collapses_duplicates() -> None:
    ds = make_dataset()
    findings = [RawFinding("STO-S02", ("const",)), RawFinding("STO-S02", ("const",))]
    assert len(normalize_findings(findings, ds)) == 1


def test_normalize_accepts_detection_result() -> None:
    from synthaudit_bench.detector import DetectionResult

    ds = make_dataset()
    result = DetectionResult(findings=(RawFinding("STO-S02", ("const",)),))
    assert len(normalize_findings(result, ds)) == 1


def test_normalize_defaults_sto_version_without_mapper() -> None:
    ds = make_dataset()
    tuples = normalize_findings([RawFinding("STO-S02", ("const",))], ds, sto_version=None)
    assert tuples[0].sto_class == "STO-S02"


def test_normalize_schema_failure_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    from synthaudit_bench.schemas.errors import SchemaValidationError

    def _boom(name: str, instance: Any, version: str | None = None) -> None:
        raise SchemaValidationError(
            schema_id="artifact-tuple", pointer="/class", value="x", explanation="no"
        )

    monkeypatch.setattr("synthaudit_bench.detector.normalize.schemas.validate_instance", _boom)
    with pytest.raises(InvalidFindingError, match="malformed finding"):
        normalize_findings([RawFinding("STO-S02", ("const",))], make_dataset())

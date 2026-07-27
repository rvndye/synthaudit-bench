"""Tests for annotation validation."""

from __future__ import annotations

from benchkit.validation import canonical_support, parse_present, validate_annotations

from _fixtures import annotation_entry


def test_valid_present_entry_passes() -> None:
    report = validate_annotations([annotation_entry()])
    assert report.ok


def test_missing_required_field_fails() -> None:
    entry = annotation_entry()
    del entry["disposition"]
    report = validate_annotations([entry])
    assert not report.ok
    assert any(i.field == "disposition" for i in report.issues)


def test_invalid_disposition_fails() -> None:
    report = validate_annotations([annotation_entry(disposition="not_a_disposition")])
    assert not report.ok
    assert any(i.field == "disposition" for i in report.issues)


def test_unknown_class_fails() -> None:
    report = validate_annotations([annotation_entry(candidate_class="STO-ZZ9")])
    assert not report.ok
    assert any(i.field == "candidate_class" for i in report.issues)


def test_present_without_evidence_fails() -> None:
    report = validate_annotations([annotation_entry(evidence="")])
    assert not report.ok
    assert any(i.field == "evidence" for i in report.issues)


def test_duplicate_detection() -> None:
    entry = annotation_entry()
    report = validate_annotations([entry, dict(entry)])
    assert not report.ok
    assert any(i.field == "duplicate" for i in report.issues)


def test_canonical_support_sorts_and_dedupes() -> None:
    assert canonical_support("b|a|a") == ("columns", "a|b")
    assert canonical_support(["c", "a"]) == ("columns", "a|c")
    assert canonical_support("<ROWS>") == ("rows", "<ROWS>")


def test_reserved_token_must_be_alone() -> None:
    report = validate_annotations([annotation_entry(support="col_a|<ROWS>")])
    assert not report.ok
    assert any(i.field == "support" for i in report.issues)


def test_parse_present_variants() -> None:
    assert parse_present("yes") is True
    assert parse_present("no") is False
    assert parse_present("maybe") is None


def test_absent_entry_needs_no_evidence() -> None:
    report = validate_annotations([annotation_entry(present="no", evidence="")])
    assert report.ok

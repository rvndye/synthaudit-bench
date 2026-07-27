"""Tests for agreement analysis."""

from __future__ import annotations

import pytest
from benchkit.agreement import analyze_agreement, cohen_kappa
from benchkit.errors import InputError

from _fixtures import annotation_entry


def test_cohen_kappa_perfect_agreement() -> None:
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0


def test_cohen_kappa_chance_level() -> None:
    # Two labels, opposite everywhere: kappa is negative (worse than chance).
    assert cohen_kappa(["a", "b"], ["b", "a"]) < 0.0


def test_cohen_kappa_single_category_degenerate() -> None:
    assert cohen_kappa(["a", "a"], ["a", "a"]) == 1.0


def test_cohen_kappa_length_mismatch_fails() -> None:
    with pytest.raises(InputError):
        cohen_kappa(["a"], ["a", "b"])


def test_full_agreement_between_annotators() -> None:
    a = [annotation_entry(annotator_id="A")]
    b = [annotation_entry(annotator_id="B")]
    report = analyze_agreement("A", a, "B", b)
    assert report.class_kappa == 1.0
    assert report.disposition_kappa == 1.0
    assert report.disagreements == ()


def test_presence_disagreement_is_reported() -> None:
    a = [annotation_entry(annotator_id="A", support="col_a")]
    b = [annotation_entry(annotator_id="B", support="col_b")]
    report = analyze_agreement("A", a, "B", b)
    assert report.n_items == 2
    kinds = {d["kind"] for d in report.disagreements}
    assert kinds == {"presence"}


def test_label_disagreement_is_reported() -> None:
    a = [annotation_entry(annotator_id="A", candidate_class="STO-P01")]
    b = [annotation_entry(annotator_id="B", candidate_class="STO-D01")]
    report = analyze_agreement("A", a, "B", b)
    assert any(d["kind"] == "label" for d in report.disagreements)


def test_agreement_generates_no_gold() -> None:
    report = analyze_agreement("A", [annotation_entry()], "B", [annotation_entry(annotator_id="B")])
    mapping = report.to_mapping()
    assert "gold" not in mapping

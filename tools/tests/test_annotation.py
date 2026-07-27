"""Tests for the annotation package generator."""

from __future__ import annotations

from benchkit.annotation import blank_form, class_options, generate_packets


def test_class_options_are_the_sixteen_sto_classes() -> None:
    options = class_options()
    assert len(options) == 16
    assert {o["id"] for o in options} >= {"STO-A06", "STO-P01", "STO-D01", "STO-S02"}
    assert all({"id", "name", "group", "gold_type"} <= set(o) for o in options)


def test_blank_form_has_no_annotations() -> None:
    form = blank_form("fx-1", columns=["a", "b"])
    assert form["annotations"] == []
    assert form["columns"] == ["a", "b"]
    assert form["disposition_options"] == [
        "target_leakage",
        "structural_constraint",
        "redundancy",
        "not_applicable",
    ]
    assert form["support_tokens"] == ["<ROWS>", "<TABLE>"]


def test_generate_packets_never_prefills() -> None:
    packets = generate_packets({"B": ["d2"], "A": ["d1", "d0"]})
    assert [p.annotator_id for p in packets] == ["A", "B"]  # deterministic order
    a = packets[0]
    assert [f["dataset_id"] for f in a.forms] == ["d0", "d1"]  # sorted
    for form in a.forms:
        assert form["annotations"] == []


def test_packets_are_deterministic() -> None:
    assignment = {"A": ["d1"], "B": ["d2"]}
    first = [p.to_mapping() for p in generate_packets(assignment)]
    second = [p.to_mapping() for p in generate_packets(assignment)]
    assert first == second


def test_bundle_manifest_is_carried_through() -> None:
    packets = generate_packets({"A": ["d1"]}, bundles={"d1": {"d1.csv": "0" * 64}})
    manifest = packets[0].manifest
    assert manifest["datasets"][0]["bundle"] == {"d1.csv": "0" * 64}

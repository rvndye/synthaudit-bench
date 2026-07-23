"""Unit tests for the declarative figure specification."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.figures import FigureInput, FigureSpec


def _spec(**overrides: object) -> FigureSpec:
    base: dict[str, object] = {
        "id": "fig1",
        "kind": "bar",
        "caption": "Artifact prevalence by generator family.",
        "inputs": (FigureInput(table="findings", columns=("generator_family", "sto_class")),),
        "encoding": {"x": "generator_family", "y": "count"},
        "params": {"stacked": True, "palette": "viridis"},
    }
    base.update(overrides)
    return FigureSpec(**base)  # type: ignore[arg-type]


def test_figure_input_round_trip() -> None:
    fin = FigureInput(table="datasets", columns=("id", "domain"))
    assert FigureInput.from_mapping(fin.to_mapping()) == fin
    bare = FigureInput(table="datasets")
    assert bare.to_mapping()["columns"] == []
    assert FigureInput.from_mapping(bare.to_mapping()) == bare


def test_figure_spec_minimal_and_full_round_trip() -> None:
    minimal = FigureSpec(id="f0", kind="scatter", caption="A caption.")
    assert minimal.to_mapping()["inputs"] == []
    assert FigureSpec.from_mapping(minimal.to_mapping()) == minimal
    assert FigureSpec.from_mapping(_spec().to_mapping()) == _spec()


def test_content_hash_is_content_addressed_and_key_order_stable() -> None:
    assert _spec().content_hash() != _spec(kind="line").content_hash()
    e1 = _spec(encoding={"x": "a", "y": "b"})
    e2 = _spec(encoding={"y": "b", "x": "a"})
    assert e1.content_hash() == e2.content_hash()
    assert len(_spec().content_hash()) == 64
    assert isinstance(_spec().to_canonical(), bytes)


def test_encoding_serializes_in_sorted_key_order() -> None:
    spec = _spec(encoding={"y": "count", "x": "family"})
    assert list(spec.to_mapping()["encoding"]) == ["x", "y"]


def test_figure_spec_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _spec().id = "x"  # type: ignore[misc]

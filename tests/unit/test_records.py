"""Unit tests for the dataset metadata record and its value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    ProvenanceConfidence,
    Task,
)
from synthaudit_bench.model.records import (
    DatasetRecord,
    License,
    Loader,
    Source,
    Transparency,
)


def _record(**overrides: object) -> DatasetRecord:
    base = {
        "id": "grid-stability-uci",
        "title": "Electrical Grid Stability",
        "frame_stratum": FrameStratum.CENSUS,
        "domain": "energy",
        "generator_family": GeneratorFamily.PHYSICS_SIMULATOR,
        "provenance_confidence": ProvenanceConfidence.DOCUMENTED,
        "task": Task.CLASSIFICATION,
        "target": "stabf",
        "license": License(name="CC BY 4.0", redistribute=True, fetch_scriptable=True),
        "source": Source(
            urls=("https://example.org/grid.csv",),
            sha256={"grid.csv": "a" * 64},
            retrieved="2026-07-23",
        ),
        "loader": Loader(format="csv", header="infer"),
        "transparency": Transparency(True, False, False, False),
        "citation": "Arzamasov 2018",
    }
    base.update(overrides)
    return DatasetRecord(**base)  # type: ignore[arg-type]


def test_record_round_trip() -> None:
    record = _record(generator_tool="Simulink 9", secondary_domains=("manufacturing",))
    assert DatasetRecord.from_mapping(record.to_mapping()) == record


def test_optional_fields_omitted_when_none() -> None:
    mapping = _record().to_mapping()
    assert "generator_tool" not in mapping
    assert "notes" not in mapping
    assert mapping["target"] == "stabf"


def test_optional_fields_present_when_set() -> None:
    mapping = _record(notes="bundled", generation_date="2018-01-01").to_mapping()
    assert mapping["notes"] == "bundled"
    assert mapping["generation_date"] == "2018-01-01"


def test_content_hash_is_content_addressed() -> None:
    assert _record().content_hash() == _record().content_hash()
    assert _record().content_hash() != _record(id="other").content_hash()
    assert len(_record().content_hash()) == 64
    assert isinstance(_record().to_canonical(), bytes)


def test_record_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _record().domain = "finance"  # type: ignore[misc]


def test_source_sha256_is_sorted_in_mapping() -> None:
    source = Source(urls=("u",), sha256={"z.csv": "1", "a.csv": "2"}, retrieved="2026-07-23")
    assert list(source.to_mapping()["sha256"]) == ["a.csv", "z.csv"]


def test_value_objects_round_trip() -> None:
    lic = License(name="Apache-2.0", redistribute=True, fetch_scriptable=True, spdx="Apache-2.0")
    assert License.from_mapping(lic.to_mapping()) == lic
    tr = Transparency(True, True, True, True)
    assert Transparency.from_mapping(tr.to_mapping()) == tr
    loader = Loader(format="csv", header=None, columns_ref="cols.txt", options={"sep": ";"})
    assert Loader.from_mapping(loader.to_mapping()) == loader
    src = Source(urls=("a",), sha256={"a": "b"}, retrieved="2026-07-23")
    assert Source.from_mapping(src.to_mapping()) == src


def test_loader_default_options_is_empty_and_immutable() -> None:
    loader = Loader(format="csv")
    assert loader.to_mapping()["options"] == {}

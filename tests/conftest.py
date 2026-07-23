"""Shared pytest configuration for the SynthAudit-Bench test suite."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

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


@pytest.fixture
def dataset_record() -> DatasetRecord:
    """A complete, valid dataset metadata record for domain-model tests."""
    return DatasetRecord(
        id="grid-stability-uci",
        title="Electrical Grid Stability",
        frame_stratum=FrameStratum.CENSUS,
        domain="energy",
        generator_family=GeneratorFamily.PHYSICS_SIMULATOR,
        provenance_confidence=ProvenanceConfidence.DOCUMENTED,
        task=Task.CLASSIFICATION,
        target="stabf",
        license=License(name="CC BY 4.0", redistribute=True, fetch_scriptable=True),
        source=Source(
            urls=("https://example.org/grid.csv",),
            sha256={"grid.csv": "a" * 64},
            retrieved="2026-07-23",
        ),
        loader=Loader(format="csv"),
        transparency=Transparency(True, False, False, False),
        citation="Arzamasov 2018",
    )


@pytest.fixture
def sto_register() -> dict[str, Any]:
    """The decoded canonical STO v1.0 register, for consistency-check fixtures.

    Tests mutate deep copies of this mapping to exercise the loader's structural
    validation without altering the packaged register.
    """
    text = (resources.files("synthaudit_bench.sto_data") / "STO-1.0.0.json").read_text(
        encoding="utf-8"
    )
    result: dict[str, Any] = json.loads(text)
    return result

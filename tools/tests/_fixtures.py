"""Isolated unit-test fixtures for benchkit.

EVERY value in this module is a synthetic, constructed fixture that exists ONLY to
exercise the tooling. Nothing here is a benchmark record, a real dataset, a real
annotation, or gold. These fixtures are never written into the benchmark data
directories and never leave the test suite.
"""

from __future__ import annotations

from typing import Any

from synthaudit_bench.canonical import sha256_bytes
from synthaudit_bench.model.records import DatasetRecord

FIXTURE_BYTES = b"col_a,col_b\n1,2\n3,4\n"
FIXTURE_SHA256 = sha256_bytes(FIXTURE_BYTES)


def record_mapping(
    dataset_id: str,
    *,
    filename: str = "d.csv",
    sha256: str = FIXTURE_SHA256,
    redistribute: bool = True,
    fetch_scriptable: bool = True,
) -> dict[str, Any]:
    """A schema-valid dataset record mapping (unit-test fixture, not a corpus record)."""
    return {
        "id": dataset_id,
        "title": f"Fixture {dataset_id}",
        "frame_stratum": "planted",
        "domain": "synthetic",
        "generator_family": "rule-based",
        "provenance_confidence": "documented",
        "modality": "tabular",
        "task": "classification",
        "target": "col_b",
        "license": {
            "name": "CC0 1.0",
            "spdx": "CC0-1.0",
            "redistribute": redistribute,
            "fetch_scriptable": fetch_scriptable,
        },
        "source": {
            "urls": [f"https://example.invalid/{dataset_id}.csv"],
            "sha256": {filename: sha256},
            "retrieved": "2026-01-01",
        },
        "loader": {"format": "csv"},
        "transparency": {
            "generator_described": True,
            "generator_code_available": True,
            "seed_reported": True,
            "artifacts_disclosed": True,
        },
        "citation": "Isolated unit-test fixture.",
    }


def dataset_record(dataset_id: str, **kwargs: Any) -> DatasetRecord:
    """A DatasetRecord built from a fixture mapping."""
    return DatasetRecord.from_mapping(record_mapping(dataset_id, **kwargs))


def annotation_entry(
    *,
    dataset_id: str = "fx-1",
    annotator_id: str = "A",
    support: Any = "col_a",
    candidate_class: str = "STO-P01",
    disposition: str = "target_leakage",
    present: Any = "yes",
    evidence: str = "fixture evidence",
    gold_type: str | None = None,
) -> dict[str, Any]:
    """A synthetic annotation entry (unit-test fixture; never a real human label)."""
    entry: dict[str, Any] = {
        "dataset_id": dataset_id,
        "annotator_id": annotator_id,
        "support": support,
        "candidate_class": candidate_class,
        "disposition": disposition,
        "present": present,
        "evidence": evidence,
    }
    if gold_type is not None:
        entry["gold_type"] = gold_type
    return entry

"""The canonical module reproduces the domain identity model exactly.

Content addressing (WP4) is the single statement of the rules the domain layer
(WP2) already applies. These tests pin that equivalence: hashing any domain
object's canonical bytes with the canonical module equals the object's own
``content_hash()``; content-only objects hash their full mapping; objects that
carry volatile run metadata exclude it from identity; and the loaded-dataset CSV
identity equals the canonical-CSV hash.
"""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd

from synthaudit_bench import canonical as c
from synthaudit_bench.model import _canonical as wp2_helper
from synthaudit_bench.model.config import Config, Pins, ResourceLimits
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.enums import Task
from synthaudit_bench.model.figures import FigureInput, FigureSpec
from synthaudit_bench.model.manifest import (
    DatasetEntry,
    Environment,
    RunManifest,
    Timestamps,
)
from synthaudit_bench.model.metrics import AggregateScores, CoverageReport, MetricsTable, Score
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.records import DatasetRecord
from synthaudit_bench.model.report import Provenance, ReportCard
from synthaudit_bench.model.results import AuditResult, DetectorInfo
from synthaudit_bench.model.tuples import ROWS, ArtifactTuple, GoldTuple


class _Addressable(Protocol):
    def to_canonical(self) -> bytes: ...
    def content_hash(self) -> str: ...


class _Mappable(_Addressable, Protocol):
    def to_mapping(self) -> dict[str, Any]: ...


_DET = DetectorInfo(name="synthaudit", version="0.1.0")
_ART = ArtifactTuple(
    support=frozenset({"stab", "stabf"}),
    sto_class="STO-A07",
    disposition=Disposition.TARGET_LEAKAGE,
)
_GOLD = GoldTuple(
    support=ROWS,
    classes=frozenset({"STO-S01"}),
    dispositions=frozenset({Disposition.NOT_APPLICABLE}),
    gold_type=GoldType.OBJECTIVE,
    evidence={"count": 0},
)
_SCORE = Score(precision=1.0, recall=1.0, f1=1.0, tp=1, fp=0, fn=0)
_AGG = AggregateScores(micro=_SCORE, macro_class_f1=1.0, macro_dataset_f1=1.0)
_METRICS = MetricsTable(
    split="public-dev", detection=_AGG, disposition_aware=_AGG, coverage=CoverageReport()
)
_CONFIG = Config(pins=Pins(bench_version="1.0.0", sto_version="1.0.0"))
_FIGURE = FigureSpec(id="f1", kind="bar", caption="x", inputs=(FigureInput(table="findings"),))
_RESULT = AuditResult(
    dataset_id="grid", dataset_sha256="a" * 64, detector=_DET, tuples=(_ART,), runtime_s=5.0
)
_REPORT = ReportCard(
    schema_version="1.0.0",
    dataset_id="grid",
    dataset_sha256="a" * 64,
    sto_version="1.0.0",
    implementation=_DET,
    target="stabf",
    task=Task.CLASSIFICATION,
    provenance=Provenance(run_timestamp="t", seed=42, config_hash="h"),
    artifacts=(_ART,),
)
_MANIFEST = RunManifest(
    bench_version="1.0.0",
    sto_version="1.0.0",
    schema_version="1.0.0",
    split="public-dev",
    detector=_DET,
    config_hash="h",
    environment=Environment(python_version="3.11", platform="linux", dependencies={}),
    root_seed=42,
    limits=ResourceLimits(),
    timestamps=Timestamps("s", "f"),
    datasets=(DatasetEntry(dataset_id="grid", sha256="a" * 64, status="ok"),),
)
_DATASET = DatasetObject(
    name="grid", table=pd.DataFrame({"a": [1, 2, 3], "stabf": ["x", "y", "x"]})
)

_ALL: list[_Addressable] = [
    _ART,
    _GOLD,
    _METRICS,
    _CONFIG,
    _FIGURE,
    _RESULT,
    _REPORT,
    _MANIFEST,
    _DATASET,
]
_CONTENT_ONLY: list[_Mappable] = [_ART, _GOLD, _METRICS, _CONFIG, _FIGURE]
_VOLATILE: list[_Mappable] = [_RESULT, _REPORT, _MANIFEST]


def test_canonical_module_matches_wp2_helper() -> None:
    mapping = {"b": 1, "a": [3, 1, 2], "z": {"k": 0.1, "j": 1.0}}
    assert c.canonical_json(mapping) == wp2_helper.canonical_bytes(mapping)
    assert c.content_hash(mapping) == wp2_helper.hash_mapping(mapping)


def test_hashing_canonical_bytes_matches_object_identity(dataset_record: DatasetRecord) -> None:
    objects: list[_Addressable] = [dataset_record, *_ALL]
    for obj in objects:
        assert c.sha256_bytes(obj.to_canonical()) == obj.content_hash()


def test_content_only_objects_hash_their_full_mapping(dataset_record: DatasetRecord) -> None:
    objects: list[_Mappable] = [dataset_record, *_CONTENT_ONLY]
    for obj in objects:
        assert c.content_hash(obj.to_mapping()) == obj.content_hash()


def test_volatile_objects_exclude_run_metadata_from_identity() -> None:
    # to_mapping carries the volatile field; identity omits it, so the hashes differ.
    for obj in _VOLATILE:
        assert c.content_hash(obj.to_mapping()) != obj.content_hash()


def test_dataset_object_csv_identity_matches_canonical_csv() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "stabf": ["x", "y", "x"]})
    obj = DatasetObject(name="grid", table=df)
    assert c.canonical_csv(df) == obj.to_canonical()
    assert obj.content_hash() == c.sha256_bytes(c.canonical_csv(df))
    assert c.verify_bytes(c.canonical_csv(df), obj.content_hash()) is True


def test_equal_domain_objects_hash_identically() -> None:
    a = ArtifactTuple(support=frozenset({"x", "y"}), sto_class="STO-A02")
    b = ArtifactTuple(support=frozenset({"y", "x"}), sto_class="STO-A02")
    assert c.content_hash(a.to_mapping()) == c.content_hash(b.to_mapping())

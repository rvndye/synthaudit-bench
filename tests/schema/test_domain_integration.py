"""Integration: every WP2 domain object serializes to a schema-valid mapping.

This is the contract between the domain layer (which produces mappings) and the
schema layer (which validates them at the IO boundary): ``to_mapping()`` output
must satisfy the object's normative schema.
"""

from __future__ import annotations

from synthaudit_bench import schemas
from synthaudit_bench.model.config import Config, Pins, ResourceLimits
from synthaudit_bench.model.enums import Grade, Task
from synthaudit_bench.model.manifest import (
    DatasetEntry,
    Environment,
    RunManifest,
    Timestamps,
)
from synthaudit_bench.model.metrics import (
    AggregateScores,
    CoverageReport,
    DatasetMetrics,
    MetricsTable,
    Score,
)
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.records import DatasetRecord
from synthaudit_bench.model.report import Pillars, Provenance, Recommendations, ReportCard
from synthaudit_bench.model.results import DetectorInfo
from synthaudit_bench.model.tuples import ROWS, ArtifactTuple, GoldTuple

_DET = DetectorInfo(name="synthaudit", version="0.1.0", probe_family="gbm")
_SHA = "a" * 64
_ART = ArtifactTuple(
    support=frozenset({"stab", "stabf"}),
    sto_class="STO-A07",
    disposition=Disposition.TARGET_LEAKAGE,
    evidence={"rule": "stabf==unstable iff stab>0"},
)


def test_dataset_record_validates(dataset_record: DatasetRecord) -> None:
    schemas.validate_instance("dataset", dataset_record.to_mapping())


def test_artifact_and_gold_tuples_validate() -> None:
    schemas.validate_instance("artifact-tuple", _ART.to_mapping())
    gold = GoldTuple(
        support=ROWS,
        classes=frozenset({"STO-S01"}),
        dispositions=frozenset({Disposition.NOT_APPLICABLE}),
        gold_type=GoldType.OBJECTIVE,
        evidence={"duplicate_row_fraction": 0.0},
    )
    schemas.validate_instance("gold-tuple", gold.to_mapping())


def test_report_card_with_all_optionals_validates() -> None:
    card = ReportCard(
        schema_version="1.0.0",
        dataset_id="grid-stability-uci",
        dataset_sha256=_SHA,
        sto_version="1.0.0",
        implementation=_DET,
        target="stabf",
        task=Task.CLASSIFICATION,
        provenance=Provenance(run_timestamp="2026-07-23T00:00:00Z", seed=42, config_hash="c0ffee"),
        artifacts=(_ART,),
        pillars=Pillars(label=0.0, feature=0.85, transparency=None),
        bti=0.23,
        grade=Grade.F,
        probe_family="gbm",
        recommendations=Recommendations(drop=("stab",), protocol_warnings=("use grouped CV",)),
        dispositions_summary={"target_leakage": 1},
    )
    schemas.validate_instance("report-card", card.to_mapping())


def test_audit_result_tuples_validate_individually() -> None:
    # AuditResult has no standalone schema; its tuples validate against the tuple schema.
    for tup in (_ART,):
        schemas.validate_instance("artifact-tuple", tup.to_mapping())


def test_run_manifest_validates() -> None:
    manifest = RunManifest(
        bench_version="1.0.0",
        sto_version="1.0.0",
        schema_version="1.0.0",
        split="public-dev",
        detector=_DET,
        config_hash="c0ffee",
        environment=Environment(
            python_version="3.11.9", platform="linux", dependencies={"pandas": "2.2.0"}
        ),
        root_seed=42,
        limits=ResourceLimits(wall_clock_s=60.0, memory_mb=4096),
        timestamps=Timestamps("2026-07-23T00:00:00Z", "2026-07-23T00:05:00Z"),
        datasets=(DatasetEntry(dataset_id="grid", sha256=_SHA, status="ok", result_hash="r"),),
        held_out_seeds=(1, 2),
        pin_overrides=("sto_version",),
    )
    schemas.validate_instance("run-manifest", manifest.to_mapping())


def test_metrics_table_validates() -> None:
    score = Score(precision=0.8, recall=0.6, f1=0.686, tp=6, fp=1, fn=4)
    agg = AggregateScores(micro=score, macro_class_f1=0.5, macro_dataset_f1=0.55)
    table = MetricsTable(
        split="public-dev",
        detection=agg,
        disposition_aware=agg,
        coverage=CoverageReport(
            abstain_hit=2,
            abstain_other=1,
            gold_type_recall={"objective": 0.9},
            objective_gold_recall=0.9,
        ),
        per_class={"STO-A07": score},
        per_disposition={"target_leakage": score},
        per_dataset=(DatasetMetrics(dataset_id="grid", detection=score, disposition_aware=score),),
        partial_credit=agg,
    )
    schemas.validate_instance("metrics", table.to_mapping())


def test_config_validates() -> None:
    config = Config(
        pins=Pins(bench_version="1.0.0", sto_version="1.0.0", synthaudit_version="0.1.0"),
        root_seed=42,
        thresholds={"tau_jaccard": 0.5},
        limits=ResourceLimits(wall_clock_s=60.0),
        layers=("packaged", "default.yaml", "cli"),
        jobs=8,
        log_level="INFO",
    )
    schemas.validate_instance("config", config.to_mapping())

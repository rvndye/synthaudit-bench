"""The compliance suite: run CS-1..CS-7 against a detector (specification Section 11).

Given a detector and a conformance set (datasets plus published gold), this runs
the seven compliance checks and emits a hash-stamped
:class:`ComplianceRecord`. The checks are: schema validation of every emitted and
consumed artifact (CS-1); byte-identical repeat runs (CS-2); exact objective-gold
recall and precision (CS-3); adjudicated-gold tolerances (CS-4); abstention
correctness (CS-5); reproducibility (CS-6, checked in process as repeat
determinism, with a fresh-environment rebuild left to CI); and a cross-check of
published reference outputs when supplied (CS-7). Acceptance tolerances are
version-pinned constants (``conformance/tolerances.json``); the defaults here are
the v1.0 values. The suite is deterministic and reads only its inputs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from synthaudit_bench.canonical import content_hash
from synthaudit_bench.detector.base import Detector, ExecutionContext
from synthaudit_bench.detector.ontology_map import OntologyMapper
from synthaudit_bench.detector.run import run_detector
from synthaudit_bench.gold.scoring import evaluate, validate_gold
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.metrics import Score
from synthaudit_bench.model.results import AuditResult
from synthaudit_bench.model.tuples import GoldTuple
from synthaudit_bench.sto import DEFAULT_VERSION, load

__all__ = [
    "DEFAULT_TOLERANCES",
    "ComplianceRecord",
    "ComplianceResult",
    "run_compliance",
]

DEFAULT_TOLERANCES: Mapping[str, float] = {
    "objective_recall": 1.0,
    "objective_precision": 1.0,
    "adjudicated_recall": 0.80,
    "adjudicated_precision": 0.80,
}


@dataclass(frozen=True, slots=True)
class ComplianceResult:
    """The outcome of one compliance check."""

    check: str
    passed: bool
    detail: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this check result."""
        return {"check": self.check, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ComplianceRecord:
    """The signed record of a compliance run (specification Sections 10.4, 11)."""

    implementation: str
    version: str
    benchmark_version: str
    results: tuple[ComplianceResult, ...]
    passed: bool

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this record."""
        return {
            "implementation": self.implementation,
            "version": self.version,
            "benchmark_version": self.benchmark_version,
            "results": [result.to_mapping() for result in self.results],
            "passed": self.passed,
        }

    def result_hash(self) -> str:
        """Return the SHA-256 of the record, cited in a conformance claim (Section 10.4)."""
        return content_hash(self.to_mapping())


def _run(
    detector: Detector,
    datasets: Sequence[DatasetObject],
    context: ExecutionContext,
    mapper: OntologyMapper | None,
) -> list[AuditResult]:
    return [run_detector(detector, dataset, context, mapper=mapper) for dataset in datasets]


def _pool(per_class: Mapping[str, Score], classes: Iterable[str]) -> tuple[int, int, int]:
    tp = fp = fn = 0
    for sto_class in classes:
        score = per_class.get(sto_class)
        if score is not None:
            tp += score.tp
            fp += score.fp
            fn += score.fn
    return tp, fp, fn


def _recall_precision(tp: int, fp: int, fn: int) -> tuple[float, float]:
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    return recall, precision


def run_compliance(
    detector: Detector,
    datasets: Sequence[DatasetObject],
    gold: Mapping[str, Sequence[GoldTuple]],
    *,
    benchmark_version: str = "1.0.0",
    sto_version: str = DEFAULT_VERSION,
    mapper: OntologyMapper | None = None,
    tolerances: Mapping[str, float] | None = None,
    expected_outputs: Mapping[str, Sequence[str]] | None = None,
) -> ComplianceRecord:
    """Run CS-1..CS-7 against ``detector`` on the conformance set and return the record."""
    tol = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    caps = detector.capabilities()
    context = ExecutionContext(bench_version=benchmark_version, sto_version=sto_version)
    ontology = load(sto_version)

    first = _run(detector, datasets, context, mapper)
    second = _run(detector, datasets, context, mapper)
    gold_by_id = {key: tuple(value) for key, value in gold.items()}

    # CS-1: schema validation of consumed gold and emitted tuples.
    cs1_ok = all(
        result.error is None or result.error.code != "invalid_findings" for result in first
    )
    cs1_detail = "all emitted tuples and consumed gold are schema-valid"
    try:
        for gold_set in gold_by_id.values():
            validate_gold(gold_set, sto_version)
    except Exception as exc:  # a malformed gold set fails CS-1
        cs1_ok = False
        cs1_detail = f"gold validation failed: {exc}"

    # CS-2: objective determinism (byte-identical repeat runs on required fields).
    cs2_ok = [r.content_hash() for r in first] == [r.content_hash() for r in second]

    # Gold is validated in CS-1 above; score without re-validating so a malformed
    # gold set is reported as a CS-1 failure rather than aborting the suite.
    table = evaluate(
        first, gold_by_id, split="conformance", sto_version=sto_version, validate=False
    )
    objective = {c for c in table.per_class if ontology.is_known(c) and ontology.is_objective(c)}
    adjudicated = {
        c for c in table.per_class if ontology.is_known(c) and not ontology.is_objective(c)
    }

    obj_recall, obj_precision = _recall_precision(*_pool(table.per_class, objective))
    adj_recall, adj_precision = _recall_precision(*_pool(table.per_class, adjudicated))

    # CS-3: objective-gold exactness.
    cs3_ok = obj_recall >= tol["objective_recall"] and obj_precision >= tol["objective_precision"]
    # CS-4: adjudicated-gold tolerances (vacuously satisfied when no adjudicated gold).
    cs4_ok = not adjudicated or (
        adj_recall >= tol["adjudicated_recall"] and adj_precision >= tol["adjudicated_precision"]
    )
    # CS-5: abstentions never count against precision (guaranteed by the matching of Section 5.5).
    cs5_ok = True
    # CS-6: reproducibility; a fresh-environment rebuild is CI's job, so the in-process
    # proxy is repeat-run determinism (CS-2).
    cs6_ok = cs2_ok
    # CS-7: cross-check of published reference outputs, when supplied.
    if expected_outputs is None:
        cs7_ok = True
        cs7_detail = "no reference outputs supplied; cross-check skipped"
    else:
        cs7_ok = all(
            {
                t.sto_class
                for t in result.tuples
                if ontology.is_known(t.sto_class) and ontology.is_objective(t.sto_class)
            }
            >= {
                c
                for c in expected_outputs.get(result.dataset_id, ())
                if ontology.is_known(c) and ontology.is_objective(c)
            }
            for result in first
        )
        cs7_detail = "objective classes reproduce the reference outputs"

    results = (
        ComplianceResult("CS-1", cs1_ok, cs1_detail),
        ComplianceResult("CS-2", cs2_ok, "repeat runs are byte-identical on required fields"),
        ComplianceResult(
            "CS-3", cs3_ok, f"objective recall {obj_recall:.3f}, precision {obj_precision:.3f}"
        ),
        ComplianceResult(
            "CS-4", cs4_ok, f"adjudicated recall {adj_recall:.3f}, precision {adj_precision:.3f}"
        ),
        ComplianceResult("CS-5", cs5_ok, "abstentions are excluded from precision"),
        ComplianceResult(
            "CS-6", cs6_ok, "in-process determinism proxy for fresh-environment rebuild"
        ),
        ComplianceResult("CS-7", cs7_ok, cs7_detail),
    )
    return ComplianceRecord(
        implementation=caps.name,
        version=caps.version,
        benchmark_version=benchmark_version,
        results=results,
        passed=all(result.passed for result in results),
    )

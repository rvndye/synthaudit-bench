"""The scoring metrics table and its embedded value objects.

``MetricsTable`` is the scored output of matching predictions against gold
(benchmark spec Section 5.6): core precision/recall/F1 at the detection and
disposition-aware levels, micro and macro aggregation, per-class and
per-disposition breakdowns, the coverage/abstention report, and the optional
partial-credit secondary metric. It is a pure record of already-computed
numbers; this module performs no scoring. Every field participates in identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping

__all__ = [
    "AggregateScores",
    "CoverageReport",
    "DatasetMetrics",
    "MetricsTable",
    "Score",
]


@dataclass(frozen=True, slots=True)
class Score:
    """A precision/recall/F1 triple with its supporting TP/FP/FN counts (spec 5.6.1)."""

    precision: float
    recall: float
    f1: float
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this score."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Score:
        """Build a score from a mapping."""
        return cls(
            precision=float(data["precision"]),
            recall=float(data["recall"]),
            f1=float(data["f1"]),
            tp=int(data.get("tp", 0)),
            fp=int(data.get("fp", 0)),
            fn=int(data.get("fn", 0)),
        )


@dataclass(frozen=True, slots=True)
class AggregateScores:
    """A micro score plus macro-by-class and macro-by-dataset F1 (spec 5.6.2)."""

    micro: Score
    macro_class_f1: float
    macro_dataset_f1: float

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these aggregate scores."""
        return {
            "micro": self.micro.to_mapping(),
            "macro_class_f1": self.macro_class_f1,
            "macro_dataset_f1": self.macro_dataset_f1,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> AggregateScores:
        """Build aggregate scores from a mapping."""
        return cls(
            micro=Score.from_mapping(data["micro"]),
            macro_class_f1=float(data["macro_class_f1"]),
            macro_dataset_f1=float(data["macro_dataset_f1"]),
        )


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Abstention counts and per-gold-type recovery fractions (spec 5.6.5)."""

    abstain_hit: int = 0
    abstain_other: int = 0
    gold_type_recall: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
    objective_gold_recall: float | None = None
    adjudicated_gold_recall: float | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this coverage report."""
        mapping: dict[str, Any] = {
            "abstain_hit": self.abstain_hit,
            "abstain_other": self.abstain_other,
            "gold_type_recall": {
                k: self.gold_type_recall[k] for k in sorted(self.gold_type_recall)
            },
        }
        if self.objective_gold_recall is not None:
            mapping["objective_gold_recall"] = self.objective_gold_recall
        if self.adjudicated_gold_recall is not None:
            mapping["adjudicated_gold_recall"] = self.adjudicated_gold_recall
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> CoverageReport:
        """Build a coverage report from a mapping."""
        return cls(
            abstain_hit=int(data.get("abstain_hit", 0)),
            abstain_other=int(data.get("abstain_other", 0)),
            gold_type_recall=MappingProxyType(dict(data.get("gold_type_recall", {}))),
            objective_gold_recall=data.get("objective_gold_recall"),
            adjudicated_gold_recall=data.get("adjudicated_gold_recall"),
        )


@dataclass(frozen=True, slots=True)
class DatasetMetrics:
    """Per-dataset detection and disposition-aware scores."""

    dataset_id: str
    detection: Score
    disposition_aware: Score
    partial_credit: Score | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these per-dataset metrics."""
        mapping: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "detection": self.detection.to_mapping(),
            "disposition_aware": self.disposition_aware.to_mapping(),
        }
        if self.partial_credit is not None:
            mapping["partial_credit"] = self.partial_credit.to_mapping()
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DatasetMetrics:
        """Build per-dataset metrics from a mapping."""
        partial = data.get("partial_credit")
        return cls(
            dataset_id=data["dataset_id"],
            detection=Score.from_mapping(data["detection"]),
            disposition_aware=Score.from_mapping(data["disposition_aware"]),
            partial_credit=Score.from_mapping(partial) if partial is not None else None,
        )


@dataclass(frozen=True, slots=True)
class MetricsTable:
    """The full metrics table for one split (spec Section 5.6)."""

    split: str
    detection: AggregateScores
    disposition_aware: AggregateScores
    coverage: CoverageReport
    per_class: Mapping[str, Score] = field(default_factory=lambda: MappingProxyType({}))
    per_disposition: Mapping[str, Score] = field(default_factory=lambda: MappingProxyType({}))
    per_dataset: tuple[DatasetMetrics, ...] = ()
    partial_credit: AggregateScores | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "per_dataset", tuple(sorted(self.per_dataset, key=lambda d: d.dataset_id))
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping for this metrics table."""
        mapping: dict[str, Any] = {
            "split": self.split,
            "detection": self.detection.to_mapping(),
            "disposition_aware": self.disposition_aware.to_mapping(),
            "coverage": self.coverage.to_mapping(),
            "per_class": {k: self.per_class[k].to_mapping() for k in sorted(self.per_class)},
            "per_disposition": {
                k: self.per_disposition[k].to_mapping() for k in sorted(self.per_disposition)
            },
            "per_dataset": [d.to_mapping() for d in self.per_dataset],
        }
        if self.partial_credit is not None:
            mapping["partial_credit"] = self.partial_credit.to_mapping()
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> MetricsTable:
        """Build a metrics table from a mapping (assumed already schema-valid)."""
        partial = data.get("partial_credit")
        return cls(
            split=data["split"],
            detection=AggregateScores.from_mapping(data["detection"]),
            disposition_aware=AggregateScores.from_mapping(data["disposition_aware"]),
            coverage=CoverageReport.from_mapping(data["coverage"]),
            per_class=MappingProxyType(
                {k: Score.from_mapping(v) for k, v in data.get("per_class", {}).items()}
            ),
            per_disposition=MappingProxyType(
                {k: Score.from_mapping(v) for k, v in data.get("per_disposition", {}).items()}
            ),
            per_dataset=tuple(DatasetMetrics.from_mapping(d) for d in data.get("per_dataset", ())),
            partial_credit=AggregateScores.from_mapping(partial) if partial is not None else None,
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of the metrics table."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 content hash of the metrics table."""
        return hash_mapping(self.to_mapping())

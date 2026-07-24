"""Metric computation from matched predictions and gold (specification Section 5.6).

Given a detector's predictions and the gold for a dataset, this module computes
true/false positives and negatives at the detection and disposition-aware levels,
precision/recall/F1 (with the convention 0/0 = 0), the secondary partial-credit
metric, per-class and per-disposition breakdowns, and the coverage/abstention
report, then pools them across a split into micro and macro aggregates. It builds
the frozen :class:`~synthaudit_bench.model.metrics.MetricsTable`; it is pure and
deterministic, and it computes nothing that the matching of Section 5.5 did not
already determine.

Abstentions (predictions classed ``ABSTAIN`` or ``STO-X00``) never count as false
positives (Section 5.5); an abstention overlapping an unmatched gold item at or
above ``tau_jaccard`` is an ``abstain_hit``, otherwise an ``abstain_other``.
Optional gold contributes a true positive when matched and is excluded from false
negatives when not.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.gold.errors import InvalidGoldError, MetricsError
from synthaudit_bench.gold.matching import (
    is_candidate_detection,
    is_candidate_disposition,
    is_candidate_partial,
    jaccard,
    match,
)
from synthaudit_bench.model.metrics import (
    AggregateScores,
    CoverageReport,
    DatasetMetrics,
    MetricsTable,
    Score,
)
from synthaudit_bench.model.results import AuditResult, DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple, GoldTuple
from synthaudit_bench.schemas.errors import SchemaValidationError
from synthaudit_bench.sto import ABSTAIN, DEFAULT_VERSION, UNCLASSIFIED, load

__all__ = [
    "Counts",
    "DetectorSummary",
    "detector_summary",
    "evaluate",
    "score_predictions",
    "validate_gold",
    "validate_metrics",
]

_RESERVED = frozenset({UNCLASSIFIED, ABSTAIN})
_SCORED_DISPOSITIONS = frozenset({"target_leakage", "structural_constraint", "redundancy"})
_TAU_JACCARD = 0.5


@dataclass(frozen=True, slots=True)
class Counts:
    """True/false positive and false negative counts, and the score they imply."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    def score(self) -> Score:
        """Return the precision/recall/F1 score (with 0/0 = 0)."""
        precision = self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0
        recall = self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        return Score(precision, recall, f1, self.tp, self.fp, self.fn)


def _bump(table: dict[str, Counts], key: str, *, tp: int = 0, fp: int = 0, fn: int = 0) -> None:
    current = table.get(key, Counts())
    table[key] = Counts(current.tp + tp, current.fp + fp, current.fn + fn)


def _sum_counts(items: Iterable[Counts]) -> Counts:
    tp = fp = fn = 0
    for item in items:
        tp += item.tp
        fp += item.fp
        fn += item.fn
    return Counts(tp, fp, fn)


def _merge_maps(maps: Iterable[Mapping[str, Counts]]) -> dict[str, Counts]:
    merged: dict[str, Counts] = {}
    for mapping in maps:
        for key, counts in mapping.items():
            _bump(merged, key, tp=counts.tp, fp=counts.fp, fn=counts.fn)
    return merged


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _disposition_value(prediction: ArtifactTuple) -> str | None:
    return prediction.disposition.value if prediction.disposition is not None else None


@dataclass(frozen=True, slots=True)
class _LevelScore:
    counts: Counts
    per_class: Mapping[str, Counts]
    per_disposition: Mapping[str, Counts]


def _score_level(
    scored: Sequence[ArtifactTuple],
    gold: Sequence[GoldTuple],
    matched: tuple[tuple[int, int], ...],
    unmatched_predictions: tuple[int, ...],
    unmatched_gold: tuple[int, ...],
) -> _LevelScore:
    per_class: dict[str, Counts] = {}
    per_disposition: dict[str, Counts] = {}
    for pred_index, _ in matched:
        _bump(per_class, scored[pred_index].sto_class, tp=1)
        value = _disposition_value(scored[pred_index])
        if value in _SCORED_DISPOSITIONS:
            _bump(per_disposition, value, tp=1)
    for pred_index in unmatched_predictions:
        _bump(per_class, scored[pred_index].sto_class, fp=1)
        value = _disposition_value(scored[pred_index])
        if value in _SCORED_DISPOSITIONS:
            _bump(per_disposition, value, fp=1)
    fn = 0
    for gold_index in unmatched_gold:
        if gold[gold_index].optional:
            continue
        fn += 1
        for sto_class in gold[gold_index].classes:
            _bump(per_class, sto_class, fn=1)
        for disposition in gold[gold_index].dispositions:
            if disposition.value in _SCORED_DISPOSITIONS:
                _bump(per_disposition, disposition.value, fn=1)
    counts = Counts(len(matched), len(unmatched_predictions), fn)
    return _LevelScore(counts, per_class, per_disposition)


@dataclass(frozen=True, slots=True)
class _DatasetScore:
    dataset_id: str
    detection: _LevelScore
    disposition: _LevelScore
    partial: _LevelScore
    abstain_hit: int
    abstain_other: int
    gold_type_total: Mapping[str, int]
    gold_type_recovered: Mapping[str, int]
    gold_classes: frozenset[str]


def _evaluate_one(
    dataset_id: str,
    predictions: Sequence[ArtifactTuple],
    gold: Sequence[GoldTuple],
    tau_jaccard: float,
) -> _DatasetScore:
    scored = [p for p in predictions if p.sto_class not in _RESERVED]
    abstentions = [p for p in predictions if p.sto_class in _RESERVED]

    mr_det = match(scored, gold, is_candidate_detection)
    mr_disp = match(scored, gold, is_candidate_disposition)
    mr_part = match(scored, gold, lambda p, g: is_candidate_partial(p, g, tau_jaccard))

    detection = _score_level(
        scored, gold, mr_det.matched, mr_det.unmatched_predictions, mr_det.unmatched_gold
    )
    disposition = _score_level(
        scored, gold, mr_disp.matched, mr_disp.unmatched_predictions, mr_disp.unmatched_gold
    )
    partial = _score_level(
        scored, gold, mr_part.matched, mr_part.unmatched_predictions, mr_part.unmatched_gold
    )

    unmatched_gold_supports = [gold[g].support for g in mr_det.unmatched_gold]
    abstain_hit = 0
    abstain_other = 0
    for abstention in abstentions:
        if any(
            jaccard(abstention.support, support) >= tau_jaccard
            for support in unmatched_gold_supports
        ):
            abstain_hit += 1
        else:
            abstain_other += 1

    matched_gold = {g for _, g in mr_det.matched}
    gold_type_total: dict[str, int] = {}
    gold_type_recovered: dict[str, int] = {}
    for index, item in enumerate(gold):
        gold_type = item.gold_type.value
        gold_type_total[gold_type] = gold_type_total.get(gold_type, 0) + 1
        if index in matched_gold:
            gold_type_recovered[gold_type] = gold_type_recovered.get(gold_type, 0) + 1

    gold_classes: frozenset[str] = (
        frozenset().union(*(g.classes for g in gold)) if gold else frozenset()
    )
    return _DatasetScore(
        dataset_id,
        detection,
        disposition,
        partial,
        abstain_hit,
        abstain_other,
        gold_type_total,
        gold_type_recovered,
        gold_classes,
    )


def _macro_class_f1(pooled: Mapping[str, Counts], classes: frozenset[str]) -> float:
    if not classes:
        return 0.0
    return _mean([pooled.get(sto_class, Counts()).score().f1 for sto_class in sorted(classes)])


def _aggregate_scores(
    micro: Counts,
    pooled_per_class: Mapping[str, Counts],
    classes: frozenset[str],
    dataset_f1: Sequence[float],
) -> AggregateScores:
    return AggregateScores(
        micro=micro.score(),
        macro_class_f1=_macro_class_f1(pooled_per_class, classes),
        macro_dataset_f1=_mean(dataset_f1),
    )


def _build_table(split: str, scores: Sequence[_DatasetScore]) -> MetricsTable:
    classes: frozenset[str] = (
        frozenset().union(*(s.gold_classes for s in scores)) if scores else frozenset()
    )
    pooled_det = _merge_maps(s.detection.per_class for s in scores)
    pooled_disp = _merge_maps(s.disposition.per_class for s in scores)
    pooled_part = _merge_maps(s.partial.per_class for s in scores)
    pooled_disposition = _merge_maps(s.disposition.per_disposition for s in scores)

    detection = _aggregate_scores(
        _sum_counts(s.detection.counts for s in scores),
        pooled_det,
        classes,
        [s.detection.counts.score().f1 for s in scores],
    )
    disposition = _aggregate_scores(
        _sum_counts(s.disposition.counts for s in scores),
        pooled_disp,
        classes,
        [s.disposition.counts.score().f1 for s in scores],
    )
    partial = _aggregate_scores(
        _sum_counts(s.partial.counts for s in scores),
        pooled_part,
        classes,
        [s.partial.counts.score().f1 for s in scores],
    )

    gold_type_total: dict[str, int] = {}
    gold_type_recovered: dict[str, int] = {}
    for score in scores:
        for key, value in score.gold_type_total.items():
            gold_type_total[key] = gold_type_total.get(key, 0) + value
        for key, value in score.gold_type_recovered.items():
            gold_type_recovered[key] = gold_type_recovered.get(key, 0) + value
    gold_type_recall = {
        key: gold_type_recovered.get(key, 0) / total for key, total in gold_type_total.items()
    }
    coverage = CoverageReport(
        abstain_hit=sum(s.abstain_hit for s in scores),
        abstain_other=sum(s.abstain_other for s in scores),
        gold_type_recall=MappingProxyType(gold_type_recall),
        objective_gold_recall=gold_type_recall.get("objective"),
        adjudicated_gold_recall=gold_type_recall.get("adjudicated"),
    )

    per_class = MappingProxyType({c: pooled_det[c].score() for c in sorted(pooled_det)})
    per_disposition = MappingProxyType(
        {d: pooled_disposition[d].score() for d in sorted(pooled_disposition)}
    )
    per_dataset = tuple(
        DatasetMetrics(
            s.dataset_id,
            s.detection.counts.score(),
            s.disposition.counts.score(),
            s.partial.counts.score(),
        )
        for s in scores
    )
    return MetricsTable(
        split=split,
        detection=detection,
        disposition_aware=disposition,
        coverage=coverage,
        per_class=per_class,
        per_disposition=per_disposition,
        per_dataset=per_dataset,
        partial_credit=partial,
    )


def validate_gold(gold: Iterable[GoldTuple], sto_version: str = DEFAULT_VERSION) -> None:
    """Validate that every gold class is a known, non-reserved class of ``sto_version``.

    Raises:
        InvalidGoldError: if a gold item uses a reserved class or an unknown class.
        OntologyError: if ``sto_version`` is not available.
    """
    ontology = load(sto_version)
    for item in gold:
        for sto_class in item.classes:
            if sto_class in _RESERVED:
                raise InvalidGoldError(f"gold must not use the reserved class {sto_class!r}")
            if not ontology.is_known(sto_class):
                raise InvalidGoldError(f"gold class {sto_class!r} is unknown in STO {sto_version}")


def validate_metrics(table: MetricsTable) -> None:
    """Validate a metrics table against the normative metrics schema, fail-closed.

    Raises:
        MetricsError: if the table does not conform to the metrics schema.
    """
    try:
        schemas.validate_instance("metrics", table.to_mapping())
    except SchemaValidationError as exc:
        raise MetricsError(f"metrics table failed schema validation: {exc}") from exc


def score_predictions(
    predictions: Sequence[ArtifactTuple],
    gold: Sequence[GoldTuple],
    *,
    dataset_id: str = "",
    tau_jaccard: float = _TAU_JACCARD,
) -> DatasetMetrics:
    """Score one dataset's predictions against its gold, returning per-dataset metrics."""
    score = _evaluate_one(dataset_id, predictions, gold, tau_jaccard)
    return DatasetMetrics(
        dataset_id,
        score.detection.counts.score(),
        score.disposition.counts.score(),
        score.partial.counts.score(),
    )


def evaluate(
    results: Iterable[AuditResult],
    gold: Mapping[str, Sequence[GoldTuple]],
    *,
    split: str,
    sto_version: str = DEFAULT_VERSION,
    tau_jaccard: float = _TAU_JACCARD,
    validate: bool = True,
) -> MetricsTable:
    """Score a split: match every result against its gold and aggregate the metrics.

    Results whose audit recorded an error, or that have no gold, are excluded from
    scoring (Section 5.9 step 9). The returned :class:`MetricsTable` is validated
    against the metrics schema before it is returned.

    Raises:
        InvalidGoldError: if ``validate`` and a gold set is malformed.
        MetricsError: if the produced table fails schema validation.
    """
    scores: list[_DatasetScore] = []
    for result in sorted(results, key=lambda r: r.dataset_id):
        if result.error is not None:
            continue
        gold_tuples = tuple(gold.get(result.dataset_id, ()))
        if not gold_tuples:
            continue
        if validate:
            validate_gold(gold_tuples, sto_version)
        scores.append(_evaluate_one(result.dataset_id, result.tuples, gold_tuples, tau_jaccard))
    table = _build_table(split, scores)
    validate_metrics(table)
    return table


@dataclass(frozen=True, slots=True)
class DetectorSummary:
    """A detector's headline scores on a split, for reporting."""

    detector: str
    version: str
    split: str
    detection_micro_f1: float
    disposition_micro_f1: float
    objective_gold_recall: float | None

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this summary."""
        return {
            "detector": self.detector,
            "version": self.version,
            "split": self.split,
            "detection_micro_f1": self.detection_micro_f1,
            "disposition_micro_f1": self.disposition_micro_f1,
            "objective_gold_recall": self.objective_gold_recall,
        }


def detector_summary(detector: DetectorInfo, table: MetricsTable) -> DetectorSummary:
    """Summarize a detector's headline metrics on a scored split."""
    return DetectorSummary(
        detector=detector.name,
        version=detector.version,
        split=table.split,
        detection_micro_f1=table.detection.micro.f1,
        disposition_micro_f1=table.disposition_aware.micro.f1,
        objective_gold_recall=table.coverage.objective_gold_recall,
    )

# Gold matching and metrics

The `synthaudit_bench.gold` package is the pure scoring layer of the benchmark: it
loads ground-truth gold tuples, matches a detector's predictions against them by
the deterministic bipartite matching of specification Section 5.5, and computes the
Section 5.6 metrics into an immutable, schema-valid `MetricsTable`. It reads only
its inputs, never a clock or a global, so re-scoring the same predictions and gold
always yields the same numbers and the same content hash.

## Loading gold

`load_gold` reads a dataset's gold from a JSON file, a decoded mapping carrying a
`gold` list, or a list of records, validating every record against the normative
gold-tuple schema (Appendix A) at the boundary and parsing it into an immutable
`GoldTuple`; a schema-invalid record fails closed. `load_gold_dir` loads every
`<root>/<id>.json` gold file keyed by dataset id. `validate_gold` additionally
checks, against a pinned ontology version, that every gold class is a known,
non-reserved STO class (gold must never use `ABSTAIN` or `STO-X00`).

## Matching

`match` computes the unique maximum-cardinality bipartite matching between
predictions and gold over candidate edges. A candidate edge exists at three levels
(Section 5.5): the detection level requires equal support (compared as sets) and
the prediction's class to be one of the gold's acceptable classes; the
disposition-aware level additionally requires an acceptable disposition; the
partial level (secondary metric only) requires an acceptable class and a support
Jaccard of at least `tau_jaccard` (0.5). Uniqueness is guaranteed by processing
gold items and their candidate predictions in the normative lexicographic key
order `(class, sorted(support), disposition)`, so the augmenting-path matching is
deterministic.

## Metrics

From a matching, true positives are the matched pairs, false positives are the
unmatched non-abstain predictions, and false negatives are the unmatched
non-optional gold items. Precision, recall, and F1 (with 0/0 = 0) are computed at
the detection and disposition-aware levels. `score_predictions` scores one
dataset; `evaluate` scores a whole split, pooling counts into the micro
aggregate, averaging per-class F1 into the macro-by-class aggregate and per-dataset
F1 into the macro-by-dataset aggregate, and reporting per-class and per-disposition
breakdowns, the secondary partial-credit metric, and the coverage report
(abstain_hit/abstain_other counts and per-gold-type recovery, with objective and
adjudicated recall reported separately). Results whose audit recorded an error, or
that have no gold, are excluded from scoring (Section 5.9 step 9). The produced
`MetricsTable` is validated against the metrics schema before it is returned; the
primary headline metric is detection micro-F1, and disposition-aware micro-F1 is
the primary leakage metric.

Optional gold (a genuinely borderline artifact) contributes a true positive when
matched but is excluded from false negatives when not, so it never penalizes a
detector. Abstentions never count as false positives: an abstention overlapping an
unmatched gold item at or above `tau_jaccard` is an `abstain_hit`, otherwise an
`abstain_other`, and both are reported but excluded from precision, recall, and F1.

The per-class breakdown attributes an unmatched multi-class gold item's false
negative to each class in its acceptable set (the standard multi-label convention);
the single-class case, which is the norm, is exact. This affects only the reported
per-class breakdown and the macro-by-class aggregate, not the primary micro or
macro-by-dataset metrics, whose definitions are fully determined by the matching.

## Public API

Loading: `load_gold`, `load_gold_dir`. Matching: `match`, `is_candidate_detection`,
`is_candidate_disposition`, `is_candidate_partial`, `jaccard`, `support_set`,
`MatchResult`. Scoring: `evaluate`, `score_predictions`, `validate_gold`,
`validate_metrics`, `detector_summary`, `Counts`. Every function is deterministic
and reads only its inputs.

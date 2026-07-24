"""Gold matching and metrics (architecture ``gold`` module; specification 5.5-5.6).

The pure scoring layer of the benchmark: load gold tuples, match a detector's
predictions against them by the deterministic bipartite matching of Section 5.5,
and compute the Section 5.6 metrics (detection and disposition-aware
precision/recall/F1, micro and macro aggregation, per-class and per-disposition
breakdowns, the secondary partial-credit metric, and the coverage/abstention
report) into an immutable, schema-valid ``MetricsTable``. Everything here is
deterministic and reads only its inputs.

Public API: ``load_gold``/``load_gold_dir``; ``match`` with the candidate
predicates and ``jaccard``; ``evaluate`` (a whole split) and ``score_predictions``
(one dataset); ``validate_gold`` and ``validate_metrics``; and ``detector_summary``.
"""

from __future__ import annotations

from synthaudit_bench.gold.errors import GoldError, InvalidGoldError, MetricsError
from synthaudit_bench.gold.loader import load_gold, load_gold_dir
from synthaudit_bench.gold.matching import (
    Candidate,
    MatchResult,
    is_candidate_detection,
    is_candidate_disposition,
    is_candidate_partial,
    jaccard,
    match,
    support_set,
)
from synthaudit_bench.gold.scoring import (
    Counts,
    DetectorSummary,
    detector_summary,
    evaluate,
    score_predictions,
    validate_gold,
    validate_metrics,
)

__all__ = [
    "Candidate",
    "Counts",
    "DetectorSummary",
    "GoldError",
    "InvalidGoldError",
    "MatchResult",
    "MetricsError",
    "detector_summary",
    "evaluate",
    "is_candidate_detection",
    "is_candidate_disposition",
    "is_candidate_partial",
    "jaccard",
    "load_gold",
    "load_gold_dir",
    "match",
    "score_predictions",
    "support_set",
    "validate_gold",
    "validate_metrics",
]

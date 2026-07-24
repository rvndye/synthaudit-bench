"""Report Card generation: pillars, the BTI, grade bands, and roles.

Builds the standardized :class:`~synthaudit_bench.model.report.ReportCard`
(specification Section 8). The Benchmark Trustworthiness Index and its grade bands
are computed exactly as in Appendix D.3: the index is the weighted geometric mean
of the available pillars, with weights L 0.30, F 0.20, H 0.20, R 0.15, I 0.15, T
0.15, a floor of 0.01, normalized by the summed weight of the pillars that are
present. A pillar that is not available is ``null`` and excluded from the index
(Appendix D.3), so a card computed from only the metadata-derived pillars is still
valid.

Two pillars are computed here because they are fully determined by inputs this
layer holds: T (transparency) is the fraction of the four disclosure booleans that
are true, and F (feature integrity) is one minus the share of non-target columns
carrying an artifact-bearing role. The learned and statistical pillars (L, H, R, I)
depend on probe families and fit statistics that the specification leaves to the
implementation (Section 10.3); they are supplied as :class:`PillarInputs` and are
``null`` when not provided. This module never runs a learner and never invents a
statistic.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from synthaudit_bench import schemas
from synthaudit_bench.model.enums import Grade, Task
from synthaudit_bench.model.ontology import ColumnRole
from synthaudit_bench.model.records import Transparency
from synthaudit_bench.model.report import Pillars, Provenance, Recommendations, ReportCard
from synthaudit_bench.model.results import DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple
from synthaudit_bench.report.errors import ReportError
from synthaudit_bench.schemas.errors import SchemaValidationError

__all__ = [
    "PillarInputs",
    "bti",
    "build_report_card",
    "dispositions_summary",
    "feature_pillar",
    "grade_for",
    "transparency_pillar",
]

_WEIGHTS: Mapping[str, float] = {"L": 0.30, "F": 0.20, "H": 0.20, "R": 0.15, "I": 0.15, "T": 0.15}
_EPSILON = 0.01
_ARTIFACT_BEARING_ROLES = frozenset(
    {
        ColumnRole.DERIVED_DETERMINISTIC,
        ColumnRole.LABEL_COMPONENT,
        ColumnRole.LEAKY_FEATURE,
        ColumnRole.DUPLICATE,
        ColumnRole.CONSTANT,
    }
)


@dataclass(frozen=True, slots=True)
class PillarInputs:
    """The learned or statistical pillar values supplied by the probe layer.

    Each is a real in ``[0, 1]`` or ``None`` when not computed. The label,
    headroom, realism, and information pillars depend on fit statistics or a
    learned probe (Appendix D.2/D.3) and are therefore provided rather than
    computed in the pure reporting layer.
    """

    label: float | None = None
    headroom: float | None = None
    realism: float | None = None
    information: float | None = None


def transparency_pillar(transparency: Transparency | None) -> float | None:
    """Return the T pillar: the fraction of the four disclosure booleans that are true.

    Returns ``None`` when the metadata is absent (Appendix D.3, T = null).
    """
    if transparency is None:
        return None
    flags = (
        transparency.generator_described,
        transparency.generator_code_available,
        transparency.seed_reported,
        transparency.artifacts_disclosed,
    )
    return sum(1 for flag in flags if flag) / len(flags)


def feature_pillar(column_roles: Mapping[str, ColumnRole] | None, n_cols: int) -> float | None:
    """Return the F pillar from column roles: one minus the artifact-bearing share.

    F = 1 - (columns with a role in {derived_deterministic, label_component,
    leaky_feature, duplicate, constant}) / max(p - 1, 1) (Appendix D.3). Returns
    ``None`` when roles are not supplied.
    """
    if column_roles is None:
        return None
    bearing = sum(1 for role in column_roles.values() if role in _ARTIFACT_BEARING_ROLES)
    # Clamp to the pillar domain [0, 1] (Appendix D.3): when the artifact-bearing count
    # exceeds ``p - 1`` (e.g. a two-column frame with two bearing columns) the raw
    # expression can fall below zero, which is not a valid pillar value.
    return max(0.0, min(1.0, 1 - bearing / max(n_cols - 1, 1)))


def bti(pillars: Pillars) -> float | None:
    """Return the Benchmark Trustworthiness Index over the available pillars (D.3).

    The index is ``exp(sum over available pillars of (w_k / W) * ln(max(v_k,
    epsilon)))`` with ``W`` the summed weight of the available pillars and
    ``epsilon = 0.01``. Returns ``None`` when no pillar is available.
    """
    values = {
        "L": pillars.label,
        "F": pillars.feature,
        "H": pillars.headroom,
        "R": pillars.realism,
        "I": pillars.information,
        "T": pillars.transparency,
    }
    available = {key: value for key, value in values.items() if value is not None}
    if not available:
        return None
    total_weight = sum(_WEIGHTS[key] for key in available)
    weighted = sum(
        (_WEIGHTS[key] / total_weight) * math.log(max(value, _EPSILON))
        for key, value in available.items()
    )
    return math.exp(weighted)


def grade_for(bti_value: float | None) -> Grade | None:
    """Return the grade band for a BTI value (Appendix D.3), or ``None`` if unavailable."""
    if bti_value is None:
        return None
    if bti_value >= 0.80:
        return Grade.A
    if bti_value >= 0.65:
        return Grade.B
    if bti_value >= 0.50:
        return Grade.C
    if bti_value >= 0.35:
        return Grade.D
    return Grade.F


def dispositions_summary(artifacts: Sequence[ArtifactTuple]) -> dict[str, int]:
    """Return a count of artifacts by disposition value (Section 8)."""
    summary: dict[str, int] = {}
    for artifact in artifacts:
        if artifact.disposition is not None:
            key = artifact.disposition.value
            summary[key] = summary.get(key, 0) + 1
    return summary


def build_report_card(
    *,
    dataset_id: str,
    dataset_sha256: str,
    sto_version: str,
    implementation: DetectorInfo,
    target: str | None,
    task: Task,
    provenance: Provenance,
    artifacts: Sequence[ArtifactTuple] = (),
    transparency: Transparency | None = None,
    column_roles: Mapping[str, ColumnRole] | None = None,
    n_cols: int = 0,
    pillar_inputs: PillarInputs | None = None,
    probe_family: str | None = None,
    recommendations: Recommendations | None = None,
    schema_version: str = "1.0.0",
    validate: bool = True,
) -> ReportCard:
    """Build a schema-valid report card, computing the pillars, BTI, and grade.

    T is computed from ``transparency`` and F from ``column_roles`` and ``n_cols``;
    L, H, R, and I are taken from ``pillar_inputs`` (``None`` when not supplied).
    The BTI and grade are computed over whatever pillars are available.

    Raises:
        ReportError: if the card does not conform to the report-card schema.
    """
    inputs = pillar_inputs if pillar_inputs is not None else PillarInputs()
    pillars = Pillars(
        label=inputs.label,
        feature=feature_pillar(column_roles, n_cols),
        headroom=inputs.headroom,
        realism=inputs.realism,
        information=inputs.information,
        transparency=transparency_pillar(transparency),
    )
    has_pillar = any(value is not None for value in pillars.to_mapping().values())
    bti_value = bti(pillars) if has_pillar else None
    card = ReportCard(
        schema_version=schema_version,
        dataset_id=dataset_id,
        dataset_sha256=dataset_sha256,
        sto_version=sto_version,
        implementation=implementation,
        target=target,
        task=task,
        provenance=provenance,
        artifacts=tuple(artifacts),
        column_roles=dict(column_roles) if column_roles is not None else None,
        dispositions_summary=dispositions_summary(artifacts) or None,
        pillars=pillars if has_pillar else None,
        bti=bti_value,
        grade=grade_for(bti_value),
        probe_family=probe_family,
        recommendations=recommendations,
    )
    if validate:
        try:
            schemas.validate_instance("report-card", card.to_mapping())
        except SchemaValidationError as exc:
            raise ReportError(f"report card failed schema validation: {exc}") from exc
    return card

"""Normalize raw detector findings into canonical benchmark artifact tuples.

This is the normalization pipeline (specification Section 5.3; architecture
``detector.normalize``). It turns each :class:`RawFinding` into a canonical
:class:`~synthaudit_bench.model.tuples.ArtifactTuple` by resolving the native
identifier to an STO class, canonicalizing the support, inferring the disposition
relative to the nominated target when the detector left it implicit and it is
decidable (Section 4.3), normalizing confidence and severity, attaching evidence,
associating the dataset identity, collapsing duplicates, ordering deterministically,
and validating every tuple against the normative tuple schema (Appendix A).

Normalization is pure and reproducible: given the same findings, dataset, mapper,
and ontology version it always returns the same ordered tuples, and it never reads
a clock, a global, or any external resource. A malformed finding fails closed with
a structured :class:`~synthaudit_bench.detector.errors.NormalizationError`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from synthaudit_bench import schemas
from synthaudit_bench.detector.base import DetectionResult, RawFinding, RawSupport
from synthaudit_bench.detector.confidence import normalize_confidence
from synthaudit_bench.detector.errors import InvalidFindingError
from synthaudit_bench.detector.ontology_map import OntologyMapper, map_to_ontology
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.enums import Severity
from synthaudit_bench.model.ontology import ArtifactGroup, Disposition
from synthaudit_bench.model.tuples import ROWS, TABLE, ArtifactTuple, Support
from synthaudit_bench.schemas.errors import SchemaValidationError
from synthaudit_bench.sto import ABSTAIN, DEFAULT_VERSION, UNCLASSIFIED, Ontology, load

__all__ = ["infer_disposition", "normalize_findings"]

_TOKENS = frozenset({ROWS, TABLE})
_RESERVED = frozenset({UNCLASSIFIED, ABSTAIN})
_TARGET_INDEPENDENT_CLASSES = frozenset({"STO-R02"})


def _canonical_support(support: RawSupport) -> Support:
    if isinstance(support, str):
        if support not in _TOKENS:
            raise InvalidFindingError(
                f"string support must be a reserved token {sorted(_TOKENS)}; "
                f"use a set of column names, got {support!r}"
            )
        return support
    if not isinstance(support, (frozenset, set, tuple, list)):
        raise InvalidFindingError(f"support must be a token or a set of columns, got {support!r}")
    columns = frozenset(str(column) for column in support)
    if not columns:
        raise InvalidFindingError("column-set support must be non-empty")
    return columns


def _is_target_independent(sto_class: str, onto: Ontology) -> bool:
    if sto_class in _TARGET_INDEPENDENT_CLASSES:
        return True
    if not onto.is_known(sto_class):
        return False
    return onto.get(sto_class).group is ArtifactGroup.S


def infer_disposition(
    sto_class: str, support: Support, target: str | None, onto: Ontology
) -> Disposition | None:
    """Infer a tuple's disposition relative to ``target`` when it is decidable.

    Returns ``None`` for reserved output symbols, ``not_applicable`` when there is
    no target or the class is target-independent (the S group and STO-R02), and
    otherwise ``target_leakage`` when the target is in the support, ``redundancy``
    for a duplicate column (STO-A08) among non-target columns, else
    ``structural_constraint``. When the target relationship cannot be decided from
    the support alone (a whole-row or whole-table token), it returns ``None`` and
    leaves the detector responsible for declaring the disposition (Section 4.3).
    """
    if sto_class in _RESERVED:
        return None
    if target is None:
        return Disposition.NOT_APPLICABLE
    if _is_target_independent(sto_class, onto):
        return Disposition.NOT_APPLICABLE
    if isinstance(support, str):
        return None
    if target in support:
        return Disposition.TARGET_LEAKAGE
    if sto_class == "STO-A08":
        return Disposition.REDUNDANCY
    return Disposition.STRUCTURAL_CONSTRAINT


def _json_primitive(value: object) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, Mapping):
        return all(isinstance(k, str) and _json_primitive(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(_json_primitive(item) for item in value)
    return False


def _check_evidence(
    evidence: str | Mapping[str, object] | None,
) -> str | Mapping[str, object] | None:
    if evidence is None or isinstance(evidence, str):
        return evidence
    if isinstance(evidence, Mapping) and _json_primitive(evidence):
        return evidence
    raise InvalidFindingError("evidence must be a string or a JSON-primitive object")


def _disposition_of(
    raw: RawFinding, sto_class: str, support: Support, target: str | None, onto: Ontology
) -> Disposition | None:
    if raw.disposition is not None:
        try:
            return Disposition(raw.disposition)
        except ValueError as exc:
            raise InvalidFindingError(f"invalid disposition {raw.disposition!r}") from exc
    return infer_disposition(sto_class, support, target, onto)


def _severity_of(raw: RawFinding) -> Severity | None:
    if raw.severity is None:
        return None
    try:
        return Severity(raw.severity)
    except ValueError as exc:
        raise InvalidFindingError(f"invalid severity {raw.severity!r}") from exc


def _to_tuple(
    raw: RawFinding,
    dataset: DatasetObject,
    mapper: OntologyMapper | None,
    sto_version: str,
    onto: Ontology,
    strict: bool,
) -> ArtifactTuple:
    sto_class = map_to_ontology(raw.identifier, mapper=mapper, sto_version=sto_version)
    support = _canonical_support(raw.support)
    disposition = _disposition_of(raw, sto_class, support, dataset.target, onto)
    severity = _severity_of(raw)
    confidence = normalize_confidence(raw.confidence, kind=raw.confidence_kind, strict=strict)
    evidence = _check_evidence(raw.evidence)
    try:
        artifact = ArtifactTuple(
            support=support,
            sto_class=sto_class,
            disposition=disposition,
            severity=severity,
            evidence=evidence,
            confidence=confidence,
        )
        schemas.validate_instance("artifact-tuple", artifact.to_mapping())
    except (ValueError, SchemaValidationError) as exc:
        raise InvalidFindingError(f"malformed finding: {exc}") from exc
    return artifact


def _iter_findings(findings: Iterable[RawFinding] | DetectionResult) -> tuple[RawFinding, ...]:
    if isinstance(findings, DetectionResult):
        return findings.findings
    return tuple(findings)


def normalize_findings(
    findings: Iterable[RawFinding] | DetectionResult,
    dataset: DatasetObject,
    *,
    mapper: OntologyMapper | None = None,
    sto_version: str | None = None,
    strict: bool = True,
) -> tuple[ArtifactTuple, ...]:
    """Normalize raw findings into deterministically ordered canonical tuples.

    Each finding's identifier is resolved to an STO class, its support is
    canonicalized, its disposition is taken from the finding or inferred when
    decidable, its confidence and severity are normalized, and its evidence is
    validated. Duplicate tuples (identical support, class, and disposition) are
    collapsed to one (Section 5.3), and every tuple is validated against the
    normative tuple schema. The result is sorted by ``(class, support, disposition)``.

    Args:
        findings: the raw findings, or a :class:`DetectionResult` wrapping them.
        dataset: the audited dataset; its target drives disposition inference and
            its content hash is the instance identity these tuples describe.
        mapper: an optional ontology mapper; without one, native STO ids pass
            through and unknown identifiers become ``STO-X00``.
        sto_version: the ontology version; defaults to the mapper's version, else
            the pinned default.
        strict: when true, an out-of-range confidence raises rather than clamps.

    Raises:
        NormalizationError: if any finding is malformed or fails the tuple schema.
    """
    resolved_version = sto_version or (
        mapper.sto_version if mapper is not None else DEFAULT_VERSION
    )
    onto = load(resolved_version)
    artifacts = [
        _to_tuple(raw, dataset, mapper, resolved_version, onto, strict)
        for raw in _iter_findings(findings)
    ]
    artifacts.sort()
    collapsed: list[ArtifactTuple] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for artifact in artifacts:
        if artifact.sort_key not in seen:
            seen.add(artifact.sort_key)
            collapsed.append(artifact)
    return tuple(collapsed)

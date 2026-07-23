"""Artifact and gold tuples: the unit of detector output and of ground truth.

An :class:`ArtifactTuple` is one detected artifact (specification 5.3); a
:class:`GoldTuple` is one ground-truth item (specification 5.4). Both are frozen
and expose ``from_mapping``/``to_mapping``/``to_canonical``/``content_hash``.
Support is either an unordered set of column names or a reserved whole-row or
whole-table token; it is compared and serialized canonically.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping
from synthaudit_bench.model.enums import Severity
from synthaudit_bench.model.ontology import Disposition, GoldType

__all__ = ["ROWS", "TABLE", "ArtifactTuple", "GoldTuple"]

ROWS = "<ROWS>"
TABLE = "<TABLE>"
_TOKENS = frozenset({ROWS, TABLE})

Support = frozenset[str] | str


def _validate_support(support: Support) -> None:
    if isinstance(support, str):
        if support not in _TOKENS:
            raise ValueError(f"token support must be one of {sorted(_TOKENS)}, got {support!r}")
    elif not support:
        raise ValueError("column-set support must be non-empty")


def _support_to_json(support: Support) -> object:
    return support if isinstance(support, str) else sorted(support)


def _support_from_json(raw: object) -> Support:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (list, tuple, frozenset, set)):
        return frozenset(str(item) for item in raw)
    raise TypeError(
        f"support must be a string token or a list of columns, got {type(raw).__name__}"
    )


def _support_sort_key(support: Support) -> tuple[str, ...]:
    return (support,) if isinstance(support, str) else tuple(sorted(support))


def _evidence_to_json(evidence: str | Mapping[str, Any] | None) -> object:
    if evidence is None or isinstance(evidence, str):
        return evidence
    return {str(k): evidence[k] for k in sorted(evidence)}


@dataclass(frozen=True, slots=True)
class ArtifactTuple:
    """One detected structural artifact.

    ``support`` is a column set or a reserved token; ``sto_class`` is an STO class
    identifier or a reserved output symbol (``STO-X00``/``ABSTAIN``). Optional
    fields carry disposition, severity, evidence, and confidence.
    """

    support: Support
    sto_class: str
    disposition: Disposition | None = None
    severity: Severity | None = None
    evidence: str | Mapping[str, Any] | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        _validate_support(self.support)
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    @property
    def sort_key(self) -> tuple[str, tuple[str, ...], str]:
        """A total-order key: (class, sorted support, disposition)."""
        disposition = self.disposition.value if self.disposition is not None else ""
        return (self.sto_class, _support_sort_key(self.support), disposition)

    def __lt__(self, other: ArtifactTuple) -> bool:
        return self.sort_key < other.sort_key

    def to_mapping(self) -> dict[str, Any]:
        """Return the fully primitive canonical mapping for this tuple."""
        mapping: dict[str, Any] = {
            "support": _support_to_json(self.support),
            "class": self.sto_class,
        }
        if self.disposition is not None:
            mapping["disposition"] = self.disposition.value
        if self.severity is not None:
            mapping["severity"] = self.severity.value
        if self.evidence is not None:
            mapping["evidence"] = _evidence_to_json(self.evidence)
        if self.confidence is not None:
            mapping["confidence"] = self.confidence
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ArtifactTuple:
        """Build a tuple from a mapping (assumed already schema-valid)."""
        disposition = data.get("disposition")
        severity = data.get("severity")
        return cls(
            support=_support_from_json(data["support"]),
            sto_class=data["class"],
            disposition=Disposition(disposition) if disposition is not None else None,
            severity=Severity(severity) if severity is not None else None,
            evidence=data.get("evidence"),
            confidence=data.get("confidence"),
        )

    def to_canonical(self) -> bytes:
        """Return the deterministic canonical serialization."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 hex digest of the canonical serialization."""
        return hash_mapping(self.to_mapping())


@dataclass(frozen=True, slots=True)
class GoldTuple:
    """One ground-truth item.

    ``classes`` is the set of acceptable STO classes and ``dispositions`` the set
    of acceptable dispositions; a prediction matches if its class and disposition
    fall within these sets. ``optional`` marks a genuinely borderline item that
    never counts against recall.
    """

    support: Support
    classes: frozenset[str]
    dispositions: frozenset[Disposition]
    gold_type: GoldType
    optional: bool = False
    evidence: str | Mapping[str, Any] | None = field(default=None)

    def __post_init__(self) -> None:
        _validate_support(self.support)
        if not self.classes:
            raise ValueError("gold tuple must list at least one acceptable class")
        if not self.dispositions:
            raise ValueError("gold tuple must list at least one acceptable disposition")

    @property
    def sort_key(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """A total-order key: (sorted support, sorted classes)."""
        return (_support_sort_key(self.support), tuple(sorted(self.classes)))

    def __lt__(self, other: GoldTuple) -> bool:
        return self.sort_key < other.sort_key

    def to_mapping(self) -> dict[str, Any]:
        """Return the fully primitive canonical mapping for this gold item."""
        mapping: dict[str, Any] = {
            "support": _support_to_json(self.support),
            "classes": sorted(self.classes),
            "dispositions": sorted(d.value for d in self.dispositions),
            "gold_type": self.gold_type.value,
            "optional": self.optional,
        }
        if self.evidence is not None:
            mapping["evidence"] = _evidence_to_json(self.evidence)
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> GoldTuple:
        """Build a gold tuple from a mapping (assumed already schema-valid)."""
        return cls(
            support=_support_from_json(data["support"]),
            classes=frozenset(str(c) for c in data["classes"]),
            dispositions=frozenset(Disposition(d) for d in data["dispositions"]),
            gold_type=GoldType(data["gold_type"]),
            optional=bool(data.get("optional", False)),
            evidence=data.get("evidence"),
        )

    def to_canonical(self) -> bytes:
        """Return the deterministic canonical serialization."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 hex digest of the canonical serialization."""
        return hash_mapping(self.to_mapping())

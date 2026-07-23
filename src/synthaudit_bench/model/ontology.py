"""Immutable domain objects for the Structural Trustworthiness Ontology (STO).

These value objects describe the ontology's classes, dispositions, and column
roles. They are pure data with complete type annotations and no dependency on
any detector or on the SynthAudit reference implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ArtifactGroup",
    "ClassDef",
    "ColumnRole",
    "Deprecation",
    "Disposition",
    "GoldType",
]


class GoldType(StrEnum):
    """How ground truth for a class is established.

    ``OBJECTIVE`` classes are machine-verifiable on the released file; their gold
    is reproducible by any implementation. ``ADJUDICATED`` classes depend on a
    learned function class and are established by human adjudication.
    """

    OBJECTIVE = "objective"
    ADJUDICATED = "adjudicated"


class ArtifactGroup(StrEnum):
    """Top-level grouping of artifact classes."""

    A = "A"  # Deterministic column relations
    S = "S"  # Sampling and marginal properties
    R = "R"  # Ordering and cross-split leakage
    P = "P"  # Predictive shortcuts


class Disposition(StrEnum):
    """A recovered relation's relation to the nominated target."""

    TARGET_LEAKAGE = "target_leakage"
    STRUCTURAL_CONSTRAINT = "structural_constraint"
    REDUNDANCY = "redundancy"
    NOT_APPLICABLE = "not_applicable"


class ColumnRole(StrEnum):
    """The single primary role a column receives for reporting."""

    TARGET = "target"
    INPUT = "input"
    DERIVED_DETERMINISTIC = "derived_deterministic"
    NEAR_DETERMINISTIC = "near_deterministic"
    LABEL_COMPONENT = "label_component"
    LEAKY_FEATURE = "leaky_feature"
    DUPLICATE = "duplicate"
    CONSTANT = "constant"
    IDENTIFIER = "identifier"
    DATETIME = "datetime"
    NO_SIGNAL = "no_signal"


@dataclass(frozen=True, slots=True)
class Deprecation:
    """Deprecation metadata for a class that is retained for compatibility."""

    since_version: str
    replaced_by: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ClassDef:
    """One artifact class in the ontology.

    Class identifiers are permanent. The ``operating_points`` are the names of the
    recommended detector tolerances relevant to the class; they are pointers to
    documentation, not part of the class definition or of ground truth.
    """

    id: str
    name: str
    group: ArtifactGroup
    gold_type: GoldType
    definition: str
    scope: str
    inclusion_criteria: str
    exclusion_criteria: str
    example: str
    counterexample: str
    relationships: tuple[str, ...]
    operating_points: tuple[str, ...]
    deprecation: Deprecation | None

    @property
    def is_objective(self) -> bool:
        """Whether this class has machine-verifiable (objective) ground truth."""
        return self.gold_type is GoldType.OBJECTIVE

    @property
    def is_deprecated(self) -> bool:
        """Whether this class is deprecated."""
        return self.deprecation is not None

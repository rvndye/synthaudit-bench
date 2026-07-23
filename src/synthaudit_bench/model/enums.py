"""Controlled-value enumerations used by the domain model.

Ontology enumerations (``Disposition``, ``ColumnRole``, ``GoldType``) live in
``model.ontology``; this module adds the metadata, severity, grade, and report
enumerations. All are string enumerations so their canonical serialization is
their value.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "FrameStratum",
    "GeneratorFamily",
    "Grade",
    "ProvenanceConfidence",
    "Severity",
    "Task",
]


class Severity(StrEnum):
    """Severity of a detected artifact (recommended mapping in the spec)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Grade(StrEnum):
    """A trustworthiness grade band for the Benchmark Trustworthiness Index."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class FrameStratum(StrEnum):
    """Which corpus stratum a dataset belongs to."""

    CENSUS = "census"
    PLANTED = "planted"
    CONTROLLED = "controlled"
    ADJUDICATED_REAL = "adjudicated_real"


class ProvenanceConfidence(StrEnum):
    """Confidence in a dataset's declared generator provenance."""

    DOCUMENTED = "documented"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Task(StrEnum):
    """The benchmark task type for a dataset."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    NONE = "none"


class GeneratorFamily(StrEnum):
    """Controlled vocabulary of synthetic-data generator families."""

    PHYSICS_SIMULATOR = "physics-simulator"
    AGENT_BASED = "agent-based"
    RULE_BASED = "rule-based"
    STATISTICAL = "statistical"
    RESAMPLING = "resampling"
    GAN = "gan"
    VAE = "vae"
    DIFFUSION = "diffusion"
    LLM = "llm"
    UNKNOWN = "unknown"

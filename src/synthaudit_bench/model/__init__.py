"""Immutable domain objects for SynthAudit-Bench.

This package is the pure domain layer (architecture Section 4): frozen,
immutable dataclasses with deterministic serialization and content-addressed
identity, and no IO, scoring, or detector logic. WP1 contributed the ontology
model and semantic versioning; WP2 adds the dataset record, artifact and gold
tuples, the loaded dataset object, audit results, report cards, run manifests,
metrics tables, figure specifications, and the resolved configuration.
"""

from __future__ import annotations

from synthaudit_bench.model.config import Config, Pins, ResourceLimits
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    Grade,
    ProvenanceConfidence,
    Severity,
    Task,
)
from synthaudit_bench.model.figures import FigureInput, FigureSpec
from synthaudit_bench.model.manifest import (
    DatasetEntry,
    Environment,
    RunManifest,
    Timestamps,
)
from synthaudit_bench.model.metrics import (
    AggregateScores,
    CoverageReport,
    DatasetMetrics,
    MetricsTable,
    Score,
)
from synthaudit_bench.model.ontology import (
    ArtifactGroup,
    ClassDef,
    ColumnRole,
    Deprecation,
    Disposition,
    GoldType,
)
from synthaudit_bench.model.records import (
    DatasetRecord,
    License,
    Loader,
    Source,
    Transparency,
)
from synthaudit_bench.model.report import (
    Pillars,
    Provenance,
    Recommendations,
    ReportCard,
)
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord
from synthaudit_bench.model.semver import Version
from synthaudit_bench.model.tuples import ROWS, TABLE, ArtifactTuple, GoldTuple

__all__ = [
    "ROWS",
    "TABLE",
    "AggregateScores",
    "ArtifactGroup",
    "ArtifactTuple",
    "AuditResult",
    "ClassDef",
    "ColumnRole",
    "Config",
    "CoverageReport",
    "DatasetEntry",
    "DatasetMetrics",
    "DatasetObject",
    "DatasetRecord",
    "Deprecation",
    "DetectorInfo",
    "Disposition",
    "Environment",
    "ErrorRecord",
    "FigureInput",
    "FigureSpec",
    "FrameStratum",
    "GeneratorFamily",
    "GoldTuple",
    "GoldType",
    "Grade",
    "License",
    "Loader",
    "MetricsTable",
    "Pillars",
    "Pins",
    "Provenance",
    "ProvenanceConfidence",
    "Recommendations",
    "ReportCard",
    "ResourceLimits",
    "RunManifest",
    "Score",
    "Severity",
    "Source",
    "Task",
    "Timestamps",
    "Transparency",
    "Version",
]

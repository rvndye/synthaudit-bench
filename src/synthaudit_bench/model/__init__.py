"""Immutable domain objects for SynthAudit-Bench.

WP1 populates the ontology model. Later work packages add the remaining domain
objects (records, tuples, results, manifests) in sibling modules.
"""

from __future__ import annotations

from synthaudit_bench.model.ontology import (
    ArtifactGroup,
    ClassDef,
    ColumnRole,
    Deprecation,
    Disposition,
    GoldType,
)
from synthaudit_bench.model.semver import Version

__all__ = [
    "ArtifactGroup",
    "ClassDef",
    "ColumnRole",
    "Deprecation",
    "Disposition",
    "GoldType",
    "Version",
]

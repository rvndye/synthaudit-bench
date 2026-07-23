"""The standardized Report Card and its value objects.

``ReportCard`` mirrors specification Section 8. Its content identity covers the
audit content (dataset reference, artifacts, roles, pillars, index, grade,
recommendations) and excludes the volatile provenance block (run timestamp,
seed, config hash), so equal audit content hashes identically. Artifacts are
normalized to canonical sorted order on construction. Pillar attributes are
named by meaning; their canonical keys are the single letters L, F, H, R, I, T.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping
from synthaudit_bench.model.enums import Grade, Task
from synthaudit_bench.model.ontology import ColumnRole
from synthaudit_bench.model.results import DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple

__all__ = ["Pillars", "Provenance", "Recommendations", "ReportCard"]


@dataclass(frozen=True, slots=True)
class Pillars:
    """The six Benchmark Trustworthiness Index pillars; each is null if uncomputed."""

    label: float | None = None
    feature: float | None = None
    headroom: float | None = None
    realism: float | None = None
    information: float | None = None
    transparency: float | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping keyed by the canonical pillar letters."""
        return {
            "L": self.label,
            "F": self.feature,
            "H": self.headroom,
            "R": self.realism,
            "I": self.information,
            "T": self.transparency,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Pillars:
        """Build pillars from a mapping keyed by the canonical letters."""
        return cls(
            label=data.get("L"),
            feature=data.get("F"),
            headroom=data.get("H"),
            realism=data.get("R"),
            information=data.get("I"),
            transparency=data.get("T"),
        )


@dataclass(frozen=True, slots=True)
class Recommendations:
    """Recommended actions: columns to drop or quarantine, the honest view, warnings."""

    drop: tuple[str, ...] = ()
    quarantine: tuple[str, ...] = ()
    honest_feature_view: tuple[str, ...] = ()
    protocol_warnings: tuple[str, ...] = ()

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these recommendations."""
        return {
            "drop": list(self.drop),
            "quarantine": list(self.quarantine),
            "honest_feature_view": list(self.honest_feature_view),
            "protocol_warnings": list(self.protocol_warnings),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Recommendations:
        """Build recommendations from a mapping."""
        return cls(
            drop=tuple(data.get("drop", ())),
            quarantine=tuple(data.get("quarantine", ())),
            honest_feature_view=tuple(data.get("honest_feature_view", ())),
            protocol_warnings=tuple(data.get("protocol_warnings", ())),
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    """Run provenance for a report card (excluded from content identity)."""

    run_timestamp: str
    seed: int
    config_hash: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this provenance."""
        return {
            "run_timestamp": self.run_timestamp,
            "seed": self.seed,
            "config_hash": self.config_hash,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Provenance:
        """Build provenance from a mapping."""
        return cls(
            run_timestamp=data["run_timestamp"],
            seed=int(data["seed"]),
            config_hash=data["config_hash"],
        )


@dataclass(frozen=True, slots=True)
class ReportCard:
    """A standardized structural-trustworthiness report for one dataset."""

    schema_version: str
    dataset_id: str
    dataset_sha256: str
    sto_version: str
    implementation: DetectorInfo
    target: str | None
    task: Task
    provenance: Provenance
    artifacts: tuple[ArtifactTuple, ...] = ()
    column_roles: Mapping[str, ColumnRole] | None = None
    dispositions_summary: Mapping[str, int] | None = None
    pillars: Pillars | None = None
    bti: float | None = None
    grade: Grade | None = None
    probe_family: str | None = None
    recommendations: Recommendations | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts)))

    def _identity_mapping(self) -> dict[str, Any]:
        mapping: dict[str, Any] = {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "dataset_sha256": self.dataset_sha256,
            "sto_version": self.sto_version,
            "implementation": self.implementation.to_mapping(),
            "target": self.target,
            "task": self.task.value,
            "artifacts": [a.to_mapping() for a in self.artifacts],
        }
        if self.column_roles is not None:
            mapping["column_roles"] = {
                k: self.column_roles[k].value for k in sorted(self.column_roles)
            }
        if self.dispositions_summary is not None:
            mapping["dispositions_summary"] = dict(sorted(self.dispositions_summary.items()))
        if self.pillars is not None:
            mapping["pillars"] = self.pillars.to_mapping()
        if self.bti is not None:
            mapping["bti"] = self.bti
        if self.grade is not None:
            mapping["grade"] = self.grade.value
        if self.probe_family is not None:
            mapping["probe_family"] = self.probe_family
        if self.recommendations is not None:
            mapping["recommendations"] = self.recommendations.to_mapping()
        return mapping

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping, including provenance."""
        mapping = self._identity_mapping()
        mapping["provenance"] = self.provenance.to_mapping()
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ReportCard:
        """Build a report card from a mapping (assumed already schema-valid)."""
        roles = data.get("column_roles")
        pillars = data.get("pillars")
        grade = data.get("grade")
        recommendations = data.get("recommendations")
        return cls(
            schema_version=data["schema_version"],
            dataset_id=data["dataset_id"],
            dataset_sha256=data["dataset_sha256"],
            sto_version=data["sto_version"],
            implementation=DetectorInfo.from_mapping(data["implementation"]),
            target=data.get("target"),
            task=Task(data["task"]),
            provenance=Provenance.from_mapping(data["provenance"]),
            artifacts=tuple(ArtifactTuple.from_mapping(a) for a in data.get("artifacts", ())),
            column_roles=(
                {k: ColumnRole(v) for k, v in roles.items()} if roles is not None else None
            ),
            dispositions_summary=(
                dict(data["dispositions_summary"])
                if data.get("dispositions_summary") is not None
                else None
            ),
            pillars=Pillars.from_mapping(pillars) if pillars is not None else None,
            bti=data.get("bti"),
            grade=Grade(grade) if grade is not None else None,
            probe_family=data.get("probe_family"),
            recommendations=(
                Recommendations.from_mapping(recommendations)
                if recommendations is not None
                else None
            ),
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of the audit content (no provenance)."""
        return canonical_bytes(self._identity_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 of the audit content (excludes provenance)."""
        return hash_mapping(self._identity_mapping())

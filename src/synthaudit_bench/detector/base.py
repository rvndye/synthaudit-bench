"""The detector protocol, capability model, execution context, and raw findings.

This module is the stable, implementation-independent seam of the benchmark: the
central :class:`Detector` protocol that any structural auditing system implements
to be scored (specification Sections 5.1 to 5.3, 10). It has no heavy
dependencies (the domain model only), so a third-party detector can implement it
without importing the benchmark's internals, and the benchmark core never imports
any specific detector.

A detector declares what it can do through immutable :class:`DetectorCapabilities`
(supported STO categories, dataset modalities, logical types, the required
benchmark and ontology versions, its own name and version, and optional or
experimental capabilities), evaluates an immutable
:class:`~synthaudit_bench.model.dataset.DatasetObject` under an immutable
:class:`ExecutionContext` (the injected seed, versions, thresholds, and optional
timeout), and emits :class:`RawFinding` objects that the normalization layer turns
into canonical artifact tuples. A detector must never mutate the dataset or any
benchmark state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.semver import Version

__all__ = [
    "BaseDetector",
    "CapabilityIssue",
    "DetectionResult",
    "Detector",
    "DetectorCapabilities",
    "DetectorMetadata",
    "ExecutionContext",
    "RawFinding",
    "RawSupport",
    "capability_issues",
    "detector_capabilities",
    "detector_metadata",
    "version_compatible",
]

RawSupport = str | frozenset[str] | tuple[str, ...]
"""A raw finding's support before canonicalization: a token or a set of columns."""

_TABULAR = "tabular"


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable configuration injected into a detector for one evaluation.

    Carries the reproducibility seed (specification Section 5.8), the benchmark
    and ontology versions in force, the recommended detector thresholds
    (Appendix D operating points), an optional per-dataset wall-clock budget in
    seconds, and the resolved configuration hash. It is the only state a detector
    receives besides the dataset; a detector never reads a global or a clock.
    """

    seed: int = 42
    bench_version: str = "1.0.0"
    sto_version: str = "1.0.0"
    thresholds: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    timeout_s: float | None = None
    config_hash: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this context."""
        mapping: dict[str, Any] = {
            "seed": self.seed,
            "bench_version": self.bench_version,
            "sto_version": self.sto_version,
            "thresholds": {key: self.thresholds[key] for key in sorted(self.thresholds)},
        }
        if self.timeout_s is not None:
            mapping["timeout_s"] = self.timeout_s
        if self.config_hash is not None:
            mapping["config_hash"] = self.config_hash
        return mapping


@dataclass(frozen=True, slots=True)
class RawFinding:
    """One artifact a detector emits, before normalization.

    ``identifier`` is the detector's native class identifier (an STO id, an alias,
    or a tool-specific token resolved by the ontology mapper). ``support`` is a
    reserved token (``<ROWS>``/``<TABLE>``) or the participating columns.
    Disposition and severity are optional plain strings (normalized to enums);
    confidence is an optional real interpreted according to ``confidence_kind``.
    """

    identifier: str
    support: RawSupport
    disposition: str | None = None
    severity: str | None = None
    evidence: str | Mapping[str, Any] | None = None
    confidence: float | None = None
    confidence_kind: str = "native"


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """A detector's full output: findings plus optional notes and a partial flag.

    A detector may return a bare iterable of :class:`RawFinding` instead; this
    richer form lets it report ``partial`` completion (specification Section 5.9,
    E-6) and free-form notes that travel into the audit result.
    """

    findings: tuple[RawFinding, ...] = ()
    notes: tuple[str, ...] = ()
    partial: bool = False


DetectionOutput = Iterable[RawFinding] | DetectionResult
"""What :meth:`Detector.detect` may return: an iterable of findings or a result."""


@dataclass(frozen=True, slots=True)
class DetectorCapabilities:
    """An immutable declaration of what a detector supports.

    ``sto_categories`` lists supported STO group letters (``A``/``S``/``R``/``P``)
    or specific class identifiers; ``modalities`` and ``logical_types`` gate the
    datasets the detector accepts; ``required_bench_version`` and the optional
    ``required_sto_version`` gate version compatibility. ``optional_capabilities``
    and ``experimental_capabilities`` advertise non-core behaviors a harness may
    negotiate. Empty ``modalities`` or ``logical_types`` means "no restriction".
    """

    name: str
    version: str
    implementation: str = ""
    required_bench_version: str = "1.0.0"
    required_sto_version: str | None = None
    sto_categories: frozenset[str] = frozenset()
    modalities: frozenset[str] = frozenset({_TABULAR})
    logical_types: frozenset[str] = frozenset()
    reference_free: bool = True
    optional_capabilities: frozenset[str] = frozenset()
    experimental_capabilities: frozenset[str] = frozenset()
    probe_family: str | None = None

    @property
    def implementation_name(self) -> str:
        """The implementation name, defaulting to the detector name."""
        return self.implementation or self.name

    def supports_modality(self, modality: str) -> bool:
        """Whether ``modality`` is accepted (empty declaration accepts all)."""
        return not self.modalities or modality in self.modalities

    def supports_logical_type(self, logical_type: str) -> bool:
        """Whether ``logical_type`` is accepted (empty declaration accepts all)."""
        return not self.logical_types or logical_type in self.logical_types

    def supports_class(self, sto_class: str) -> bool:
        """Whether a class id is covered, by exact id or by its group letter."""
        if not self.sto_categories:
            return True
        if sto_class in self.sto_categories:
            return True
        group = sto_class[4:5] if sto_class.startswith("STO-") else ""
        return group in self.sto_categories

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for these capabilities."""
        mapping: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "implementation": self.implementation_name,
            "required_bench_version": self.required_bench_version,
            "sto_categories": sorted(self.sto_categories),
            "modalities": sorted(self.modalities),
            "logical_types": sorted(self.logical_types),
            "reference_free": self.reference_free,
            "optional_capabilities": sorted(self.optional_capabilities),
            "experimental_capabilities": sorted(self.experimental_capabilities),
        }
        if self.required_sto_version is not None:
            mapping["required_sto_version"] = self.required_sto_version
        if self.probe_family is not None:
            mapping["probe_family"] = self.probe_family
        return mapping


@dataclass(frozen=True, slots=True)
class DetectorMetadata:
    """A detector's identity and version report (specification Section 9.6).

    A compact projection of :class:`DetectorCapabilities` naming who the detector
    is and which benchmark and ontology versions it targets, for run manifests and
    reproducibility records.
    """

    name: str
    version: str
    implementation: str
    required_bench_version: str
    required_sto_version: str | None
    reference_free: bool

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this metadata."""
        mapping: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "implementation": self.implementation,
            "required_bench_version": self.required_bench_version,
            "reference_free": self.reference_free,
        }
        if self.required_sto_version is not None:
            mapping["required_sto_version"] = self.required_sto_version
        return mapping


@runtime_checkable
class Detector(Protocol):
    """The stable interface every scored auditing system implements.

    A detector declares :meth:`capabilities` and evaluates a dataset with
    :meth:`detect`. ``detect`` MUST be reference-free (it reads only the dataset it
    is given), deterministic given the dataset and ``context.seed`` (Section 5.8),
    and MUST NOT mutate the dataset or any benchmark state; it MAY raise, and the
    runner isolates the failure. Objective-class detection MUST use full data.

    Two optional lifecycle hooks, :meth:`setup` and :meth:`teardown`, are honored
    by :func:`~synthaudit_bench.detector.run.run_detector` when present, for
    initialization (configuration injection) and graceful shutdown.
    """

    def capabilities(self) -> DetectorCapabilities:
        """Return this detector's immutable capability declaration."""
        ...  # pragma: no cover - protocol stub

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> DetectionOutput:
        """Evaluate ``dataset`` and emit raw findings (or a detection result)."""
        ...  # pragma: no cover - protocol stub


class BaseDetector:
    """An optional convenience base with no-op lifecycle hooks.

    Subclassing is not required (implementing the :class:`Detector` protocol is
    enough), but it provides default :meth:`setup` and :meth:`teardown` so a
    detector only has to define :meth:`capabilities` and :meth:`detect`.
    """

    def setup(self, context: ExecutionContext) -> None:
        """Initialize the detector for a run (configuration injection); a no-op."""

    def teardown(self) -> None:
        """Release any resources after a run (graceful shutdown); a no-op."""

    def capabilities(self) -> DetectorCapabilities:  # pragma: no cover - abstract stub
        """Return the detector's capabilities (subclasses must override)."""
        raise NotImplementedError

    def detect(
        self, dataset: DatasetObject, context: ExecutionContext
    ) -> DetectionOutput:  # pragma: no cover - abstract stub
        """Evaluate the dataset (subclasses must override)."""
        raise NotImplementedError


def detector_capabilities(detector: Detector) -> DetectorCapabilities:
    """Return ``detector``'s capability declaration."""
    return detector.capabilities()


def detector_metadata(detector: Detector) -> DetectorMetadata:
    """Return ``detector``'s identity and version metadata."""
    caps = detector.capabilities()
    return DetectorMetadata(
        name=caps.name,
        version=caps.version,
        implementation=caps.implementation_name,
        required_bench_version=caps.required_bench_version,
        required_sto_version=caps.required_sto_version,
        reference_free=caps.reference_free,
    )


@dataclass(frozen=True, slots=True)
class CapabilityIssue:
    """One reason a detector is incompatible with a run, for negotiation."""

    code: str
    detail: str


def version_compatible(available: str, required: str) -> bool:
    """Return whether ``available`` satisfies ``required`` (additive-minor rule).

    Both are ``MAJOR.MINOR.PATCH`` strings; compatibility means the same major and
    an available version at least the required one (the governance rule of
    :meth:`synthaudit_bench.model.semver.Version.satisfies`). A malformed version
    string is treated as incompatible.
    """
    from synthaudit_bench.errors import VersionError

    try:
        return Version.parse(available).satisfies(Version.parse(required))
    except VersionError:
        return False


def capability_issues(
    caps: DetectorCapabilities,
    context: ExecutionContext,
    *,
    modality: str | None = None,
    logical_types: frozenset[str] | None = None,
) -> tuple[CapabilityIssue, ...]:
    """Return every reason ``caps`` is incompatible with ``context`` (may be empty).

    Checks benchmark-version and (when declared) ontology-version compatibility
    always, and, when a dataset ``modality`` and its ``logical_types`` are
    supplied, that the detector accepts them. An empty result means the detector
    may run. This is the non-raising core of capability negotiation.
    """
    issues: list[CapabilityIssue] = []
    if not version_compatible(context.bench_version, caps.required_bench_version):
        issues.append(
            CapabilityIssue(
                "unsupported_version",
                f"detector requires benchmark {caps.required_bench_version!r}, "
                f"run offers {context.bench_version!r}",
            )
        )
    if caps.required_sto_version is not None and not version_compatible(
        context.sto_version, caps.required_sto_version
    ):
        issues.append(
            CapabilityIssue(
                "unsupported_version",
                f"detector requires ontology {caps.required_sto_version!r}, "
                f"run offers {context.sto_version!r}",
            )
        )
    if modality is not None and not caps.supports_modality(modality):
        issues.append(
            CapabilityIssue(
                "unsupported_capability",
                f"detector does not support modality {modality!r}",
            )
        )
    if logical_types is not None:
        unsupported = sorted(t for t in logical_types if not caps.supports_logical_type(t))
        if unsupported:
            issues.append(
                CapabilityIssue(
                    "unsupported_capability",
                    f"detector does not support logical types {unsupported}",
                )
            )
    return tuple(issues)

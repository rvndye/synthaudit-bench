"""The detector protocol and result-normalization subsystem (architecture L3).

This package defines the stable, implementation-independent interface any
structural auditing system implements to be scored against SynthAudit-Bench, and
the pipeline that turns raw detector output into canonical, schema-valid artifact
tuples. It is detector-agnostic: the benchmark core never imports a specific
detector, detectors are discovered through the ``synthaudit_bench.detectors``
entry-point group, and the reference SynthAudit adapter (an optional extra, the
only component that imports the reference implementation) uses exactly this public
protocol.

Public surface: the :class:`Detector` protocol with :class:`DetectorCapabilities`,
:class:`ExecutionContext`, :class:`RawFinding`, and :class:`DetectionResult`;
registration and discovery (:func:`register_detector`, :func:`discover_detectors`,
:class:`DetectorRegistry`); execution (:func:`run_detector`,
:func:`validate_detector`); and normalization (:func:`normalize_findings`,
:func:`map_to_ontology`, :func:`normalize_confidence`, :func:`detector_capabilities`,
:func:`detector_metadata`).
"""

from __future__ import annotations

from synthaudit_bench.detector.base import (
    BaseDetector,
    CapabilityIssue,
    DetectionResult,
    Detector,
    DetectorCapabilities,
    DetectorMetadata,
    ExecutionContext,
    RawFinding,
    RawSupport,
    capability_issues,
    detector_capabilities,
    detector_metadata,
    version_compatible,
)
from synthaudit_bench.detector.confidence import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    Confidence,
    ConfidenceKind,
    normalize_confidence,
)
from synthaudit_bench.detector.errors import (
    CapabilityError,
    ConfidenceError,
    DetectorError,
    DetectorInitError,
    DetectorRuntimeError,
    DetectorTimeoutError,
    InvalidFindingError,
    InvalidOntologyIdError,
    NormalizationError,
    RegistrationError,
    UnknownDetectorError,
    UnsupportedCapabilityError,
    UnsupportedVersionError,
)
from synthaudit_bench.detector.normalize import infer_disposition, normalize_findings
from synthaudit_bench.detector.ontology_map import (
    OntologyMapper,
    build_ontology_mapper,
    identity_mapper,
    map_to_ontology,
)
from synthaudit_bench.detector.registry import (
    DETECTOR_ENTRY_POINT_GROUP,
    DetectorFactory,
    DetectorRegistry,
    discover_detectors,
    register_detector,
)
from synthaudit_bench.detector.run import run_detector, validate_detector

__all__ = [
    "CONFIDENCE_MAX",
    "CONFIDENCE_MIN",
    "DETECTOR_ENTRY_POINT_GROUP",
    "BaseDetector",
    "CapabilityError",
    "CapabilityIssue",
    "Confidence",
    "ConfidenceError",
    "ConfidenceKind",
    "DetectionResult",
    "Detector",
    "DetectorCapabilities",
    "DetectorError",
    "DetectorFactory",
    "DetectorInitError",
    "DetectorMetadata",
    "DetectorRegistry",
    "DetectorRuntimeError",
    "DetectorTimeoutError",
    "ExecutionContext",
    "InvalidFindingError",
    "InvalidOntologyIdError",
    "NormalizationError",
    "OntologyMapper",
    "RawFinding",
    "RawSupport",
    "RegistrationError",
    "UnknownDetectorError",
    "UnsupportedCapabilityError",
    "UnsupportedVersionError",
    "build_ontology_mapper",
    "capability_issues",
    "detector_capabilities",
    "detector_metadata",
    "discover_detectors",
    "identity_mapper",
    "infer_disposition",
    "map_to_ontology",
    "normalize_confidence",
    "normalize_findings",
    "register_detector",
    "run_detector",
    "validate_detector",
    "version_compatible",
]

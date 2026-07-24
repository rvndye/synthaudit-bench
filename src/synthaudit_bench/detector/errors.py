"""Structured error taxonomy for the detector protocol and normalization layer.

Every failure this subsystem raises is one of these types, so a harness can
handle detector failures exhaustively and, above all, isolate them: one
detector's failure is turned into a structured record and never terminates a
batch (specification Section 5.9). All types subclass
:class:`synthaudit_bench.errors.SynthAuditBenchError`.

The classes carry a ``code`` string that matches the benchmark's dataset-level
failure vocabulary (specification Section 5.9): a timeout maps to ``resource``, a
detector exception to ``runtime``, an ingestion problem to ``ingest``, and so on.
The code is what a wrapped :class:`~synthaudit_bench.model.results.ErrorRecord`
reports.
"""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = [
    "CapabilityError",
    "ConfidenceError",
    "DetectorError",
    "DetectorInitError",
    "DetectorRuntimeError",
    "DetectorTimeoutError",
    "InvalidFindingError",
    "InvalidOntologyIdError",
    "NormalizationError",
    "RegistrationError",
    "UnknownDetectorError",
    "UnsupportedCapabilityError",
    "UnsupportedVersionError",
]


class DetectorError(SynthAuditBenchError):
    """Base class for every detector-protocol and normalization failure."""

    code = "detector"


class DetectorInitError(DetectorError):
    """A detector's initialization (setup/configuration injection) failed."""

    code = "init"


class CapabilityError(DetectorError):
    """A detector's declared capabilities are incompatible with the run."""

    code = "capability"


class UnsupportedVersionError(CapabilityError):
    """The detector requires a benchmark or ontology version the run cannot offer."""

    code = "unsupported_version"


class UnsupportedCapabilityError(CapabilityError):
    """The detector does not support the dataset's modality or logical types."""

    code = "unsupported_capability"


class DetectorTimeoutError(DetectorError):
    """A detector exceeded its wall-clock budget (specification Section 5.9, E-4)."""

    code = "resource"


class DetectorRuntimeError(DetectorError):
    """A detector raised during evaluation, or mutated the immutable dataset."""

    code = "runtime"


class NormalizationError(DetectorError):
    """Raw detector output could not be normalized into canonical findings."""

    code = "normalization"


class InvalidFindingError(NormalizationError):
    """A raw finding is malformed (bad support, evidence, or schema violation)."""

    code = "invalid_findings"


class InvalidOntologyIdError(NormalizationError):
    """An ontology mapping targets an identifier that is not a valid STO class."""

    code = "invalid_ontology_id"


class ConfidenceError(NormalizationError):
    """A confidence value is outside the benchmark's ``[0, 1]`` bound or not finite."""

    code = "invalid_confidence"


class RegistrationError(DetectorError):
    """A detector could not be registered (for example a duplicate name)."""

    code = "registration"


class UnknownDetectorError(DetectorError):
    """A requested detector name is not registered."""

    code = "unknown_detector"

"""Fail-closed error taxonomy for benchkit.

Every tool raises a :class:`BenchkitError` (or a subclass) on any condition it
cannot handle deterministically and correctly. There is no silent recovery and no
inferred metadata: a tool either produces a verified result or fails loudly.
"""

from __future__ import annotations


class BenchkitError(Exception):
    """Base class for every benchkit failure."""


class InputError(BenchkitError):
    """A required input is missing, empty, or malformed."""


class MissingInputError(InputError):
    """A required input path or artifact does not exist (fail closed, never invent)."""


class IntegrityError(BenchkitError):
    """A hash, checksum, or content-identity check failed."""


class LicenseError(BenchkitError):
    """A license gate rejected an artifact (redistribution or scripted fetch forbidden)."""


class ValidationError(BenchkitError):
    """An artifact failed schema or semantic validation."""


class AcquisitionError(BenchkitError):
    """An artifact could not be acquired; recorded as a structured failure."""


class ReproducibilityError(BenchkitError):
    """A reproducibility check produced non-identical outputs."""

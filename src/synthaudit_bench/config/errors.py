"""Structured errors for the configuration subsystem.

All extend :class:`synthaudit_bench.errors.SynthAuditBenchError`, so callers can
handle the whole category or discriminate an unknown profile, a forbidden pin
change, or an invalid resolved configuration.
"""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = ["ConfigError", "PinOverrideError", "UnknownProfileError"]


class ConfigError(SynthAuditBenchError):
    """A configuration could not be loaded, resolved, or validated."""


class PinOverrideError(ConfigError):
    """A non-base layer tried to change a version pin without an explicit override."""


class UnknownProfileError(ConfigError):
    """A requested profile does not exist under the configuration root."""

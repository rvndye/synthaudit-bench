"""Unit tests for the error taxonomy."""

from __future__ import annotations

from synthaudit_bench.errors import (
    OntologyError,
    SchemaError,
    SynthAuditBenchError,
    VersionError,
)


def test_all_errors_share_the_base() -> None:
    for exc in (SchemaError, OntologyError, VersionError):
        assert issubclass(exc, SynthAuditBenchError)


def test_errors_carry_messages() -> None:
    assert str(OntologyError("boom")) == "boom"

"""Structured errors for the schema subsystem.

All extend :class:`synthaudit_bench.errors.SchemaError`, so callers that handle
``SchemaError`` handle these too; the subtypes let callers distinguish an unknown
schema name, an incompatible version request, a malformed schema document, and a
failed instance validation, and carry the structured location of a failure.
"""

from __future__ import annotations

from typing import Any

from synthaudit_bench.errors import SchemaError

__all__ = [
    "InvalidSchemaError",
    "SchemaCompatibilityError",
    "SchemaValidationError",
    "UnknownSchemaError",
]


class UnknownSchemaError(SchemaError):
    """A requested schema name is not registered."""


class SchemaCompatibilityError(SchemaError):
    """No registered version of a schema satisfies the requested version."""


class InvalidSchemaError(SchemaError):
    """A registered schema document is not a valid Draft 2020-12 schema."""


class SchemaValidationError(SchemaError):
    """An instance failed validation against a named schema.

    The error carries the structured location of the first failure, ordered
    deterministically by JSON pointer: the schema identifier, a JSON pointer to
    the offending location, the offending value at that location, and the
    human-readable explanation from the validator.
    """

    def __init__(self, *, schema_id: str, pointer: str, value: Any, explanation: str) -> None:
        self.schema_id = schema_id
        self.pointer = pointer
        self.value = value
        self.explanation = explanation
        super().__init__(f"{schema_id}{pointer}: {explanation}")

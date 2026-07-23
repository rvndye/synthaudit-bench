"""JSON Schema validation against the normative Draft 2020-12 schemas.

Pure validation helpers used at every IO boundary (per the architecture's
validate-at-boundaries invariant). Validation is deterministic: when an instance
is invalid, the first error by JSON-pointer order is reported, so the same input
always yields the same message.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema.exceptions import SchemaError as _JsonSchemaError
from jsonschema.validators import Draft202012Validator

from synthaudit_bench.errors import SchemaError

__all__ = ["check_schema", "validate"]


def check_schema(schema: Mapping[str, Any]) -> None:
    """Verify that ``schema`` is itself a valid Draft 2020-12 JSON Schema.

    Raises:
        SchemaError: if the schema is not well formed.
    """
    try:
        Draft202012Validator.check_schema(schema)
    except _JsonSchemaError as exc:
        raise SchemaError(f"invalid schema: {exc.message}") from exc


def validate(instance: Any, schema: Mapping[str, Any], *, label: str = "instance") -> None:
    """Validate ``instance`` against ``schema``.

    On failure the first error, ordered deterministically by JSON pointer then
    message, is raised with its pointer in the message.

    Raises:
        SchemaError: if ``instance`` does not satisfy ``schema``.
    """
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda err: ([str(part) for part in err.absolute_path], err.message),
    )
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(part) for part in first.absolute_path)
        raise SchemaError(f"{label}{pointer}: {first.message}")

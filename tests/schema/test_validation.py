"""Schema-tier tests for the generic JSON Schema validation helpers."""

from __future__ import annotations

import pytest

from synthaudit_bench.errors import SchemaError
from synthaudit_bench.schemas import check_schema, validate

_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["a", "b"],
    "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
    "additionalProperties": False,
}


def test_valid_instance_passes() -> None:
    validate({"a": "x", "b": 1}, _SCHEMA)  # no exception


def test_invalid_instance_reports_pointer() -> None:
    with pytest.raises(SchemaError) as info:
        validate({"a": 1, "b": 1}, _SCHEMA, label="doc")
    assert "doc/a" in str(info.value)


def test_missing_required_is_rejected() -> None:
    with pytest.raises(SchemaError):
        validate({"a": "x"}, _SCHEMA)


def test_error_selection_is_deterministic() -> None:
    bad = {"a": 1, "b": "not-int"}
    messages = {str(_capture(bad)) for _ in range(5)}
    assert len(messages) == 1  # same first error every time


def test_check_schema_accepts_valid_schema() -> None:
    check_schema(_SCHEMA)  # no exception


def test_check_schema_rejects_invalid_schema() -> None:
    with pytest.raises(SchemaError):
        check_schema({"type": "not-a-real-type"})


def _capture(instance: object) -> str:
    try:
        validate(instance, _SCHEMA)
    except SchemaError as exc:
        return str(exc)
    return ""

"""Unit tests for the schema registry: loading, versioning, caching, validation."""

from __future__ import annotations

import contextlib
import copy

import pytest

from synthaudit_bench import schemas
from synthaudit_bench.model.semver import Version
from synthaudit_bench.schemas.errors import (
    InvalidSchemaError,
    SchemaCompatibilityError,
    SchemaValidationError,
    UnknownSchemaError,
)
from synthaudit_bench.schemas.registry import Schema, SchemaRegistry, default_registry

_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_EXPECTED = (
    "artifact-tuple",
    "config",
    "dataset",
    "gold-tuple",
    "metrics",
    "ontology",
    "report-card",
    "run-manifest",
)


def _doc(
    schema_id: str | None = None, *, version: str | None = None, **extra: object
) -> dict[str, object]:
    doc: dict[str, object] = {"$schema": _DRAFT, "type": "object"}
    if schema_id is not None:
        doc["$id"] = schema_id
    if version is not None:
        doc["version"] = version
    doc.update(extra)
    return doc


def _versioned(name: str, minor: int) -> tuple[str, dict[str, object]]:
    ver = f"1.{minor}.0"
    return name, _doc(f"https://ex/v1.{minor}/{name}.json", version=ver)


# --- discovery and packaged data ------------------------------------------------


def test_packaged_registry_discovers_every_normative_schema() -> None:
    assert schemas.list_schemas() == _EXPECTED
    assert schemas.supported_versions() == ("1.0.0",)


def test_default_registry_is_cached_singleton() -> None:
    assert default_registry() is default_registry()


def test_from_package_data_is_deterministic() -> None:
    a = SchemaRegistry.from_package_data()
    b = SchemaRegistry.from_package_data()
    assert a.list_schemas() == b.list_schemas()
    for name in a.list_schemas():
        assert a.load_schema(name) == b.load_schema(name)
        assert a.load_schema(name).json_text == b.load_schema(name).json_text


# --- version parsing and resolution --------------------------------------------


def test_version_from_id_when_no_version_key() -> None:
    reg = SchemaRegistry([("thing", _doc("https://ex/v2.1.3/thing.json"))])
    assert reg.schema_version("thing") == "2.1.3"


def test_ontology_version_derived_from_id() -> None:
    assert schemas.schema_version("ontology") == "1.0.0"


def test_version_falls_back_when_absent_everywhere() -> None:
    reg = SchemaRegistry([("bare", _doc())])  # no $id, no version
    assert reg.schema_version("bare") == "1.0.0"
    assert reg.list_schemas() == ("bare",)


def test_version_resolution_picks_highest_compatible() -> None:
    reg = SchemaRegistry([_versioned("thing", 0), _versioned("thing", 2)])
    assert reg.available_versions("thing") == ("1.0.0", "1.2.0")
    assert reg.load_schema("thing").version == Version(1, 2, 0)  # latest
    assert reg.load_schema("thing", "1.0.0").version == Version(1, 2, 0)  # additive-minor
    assert reg.schema_version("thing", "1.2.0") == "1.2.0"


def test_incompatible_version_request_raises() -> None:
    reg = SchemaRegistry([_versioned("thing", 0)])
    with pytest.raises(SchemaCompatibilityError, match="satisfies"):
        reg.load_schema("thing", "2.0.0")


def test_is_compatible_across_major_boundary() -> None:
    v2 = ("thing", _doc("https://ex/v2.0/thing.json", version="2.0.0"))
    reg = SchemaRegistry([_versioned("thing", 1), v2])
    assert reg.is_compatible("thing", "1.0.0") is True  # satisfied by 1.1.0
    assert reg.is_compatible("thing", "2.0.0") is True  # satisfied by 2.0.0
    assert reg.is_compatible("thing", "1.2.0") is False  # 1.1.0 too low, 2.0.0 wrong major
    assert reg.is_compatible("missing", "1.0.0") is False
    assert reg.load_schema("thing", "2.0.0").version == Version(2, 0, 0)


def test_unknown_schema_name_raises_everywhere() -> None:
    reg = default_registry()
    with pytest.raises(UnknownSchemaError, match="unknown schema"):
        reg.load_schema("nope")
    with pytest.raises(UnknownSchemaError):
        reg.available_versions("nope")


# --- immutability and caching --------------------------------------------------


def test_get_schema_returns_isolated_copies() -> None:
    first = schemas.get_schema("dataset")
    first["injected"] = True
    assert "injected" not in schemas.get_schema("dataset")


def test_schema_as_dict_is_fresh_each_call() -> None:
    schema = schemas.load_schema("config")
    one = schema.as_dict()
    one["mutated"] = 1
    assert "mutated" not in schema.as_dict()
    assert isinstance(schema, Schema)


def test_validator_is_cached_per_schema() -> None:
    reg = SchemaRegistry.from_package_data()
    assert reg._validators == {}
    reg.validate("artifact-tuple", {"support": ["a"], "class": "STO-A01"})
    reg.validate("artifact-tuple", {"support": ["b"], "class": "STO-A02"})
    assert list(reg._validators) == [("artifact-tuple", Version(1, 0, 0))]


# --- validation, structured errors, no mutation --------------------------------


def test_valid_instances_pass() -> None:
    schemas.validate_instance("artifact-tuple", {"support": "<ROWS>", "class": "STO-S01"})
    schemas.validate_instance(
        "gold-tuple",
        {
            "support": ["a"],
            "classes": ["STO-A01"],
            "dispositions": ["redundancy"],
            "gold_type": "objective",
            "evidence": "identity a=b",
        },
    )


def test_invalid_object_raises_structured_error_with_pointer() -> None:
    with pytest.raises(SchemaValidationError) as excinfo:
        schemas.validate_instance("artifact-tuple", {"support": ["a"], "class": "BOGUS"})
    err = excinfo.value
    assert err.schema_id.endswith("artifact-tuple.json")
    assert err.pointer == "/class"
    assert err.value == "BOGUS"
    assert "does not match" in err.explanation
    assert str(err).endswith(err.explanation)


def test_nested_pointer_reports_deep_location() -> None:
    card = {
        "schema_version": "1.0.0",
        "dataset_id": "d",
        "dataset_sha256": "a" * 64,
        "sto_version": "1.0.0",
        "implementation": {"name": "x", "version": "1"},
        "target": None,
        "task": "none",
        "artifacts": [{"support": ["a"], "class": "not-a-class"}],
        "provenance": {"run_timestamp": "t", "seed": 0, "config_hash": "h"},
    }
    with pytest.raises(SchemaValidationError) as excinfo:
        schemas.validate_instance("report-card", card)
    assert excinfo.value.pointer == "/artifacts/0/class"


def test_missing_required_reports_root_pointer() -> None:
    with pytest.raises(SchemaValidationError) as excinfo:
        schemas.validate_instance("artifact-tuple", {"support": ["a"]})  # no class
    assert excinfo.value.pointer == "/"


def test_validation_never_mutates_input() -> None:
    for instance in ({"support": ["a"], "class": "STO-A01"}, {"support": ["a"], "class": "BAD"}):
        before = copy.deepcopy(instance)
        with contextlib.suppress(SchemaValidationError):
            schemas.validate_instance("artifact-tuple", instance)
        assert instance == before


# --- invalid and unknown schemas -----------------------------------------------


def test_registering_a_malformed_schema_raises_invalid_schema() -> None:
    with pytest.raises(InvalidSchemaError, match="not valid"):
        SchemaRegistry([("bad", {"$schema": _DRAFT, "type": 123})])


def test_registry_without_ids_builds_empty_reference_set() -> None:
    reg = SchemaRegistry([("x", _doc())])  # no $id anywhere
    reg.validate("x", {"any": "object"})
    assert reg.list_schemas() == ("x",)


def test_unknown_schema_validation_raises() -> None:
    with pytest.raises(UnknownSchemaError):
        schemas.validate_instance("does-not-exist", {})


def test_backward_compatible_primitives_are_exported() -> None:
    # The WP1 low-level primitives remain importable from the package root.
    schemas.check_schema({"$schema": _DRAFT, "type": "object"})
    schemas.validate({"k": 1}, {"type": "object", "required": ["k"]})

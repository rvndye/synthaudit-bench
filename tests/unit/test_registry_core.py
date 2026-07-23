"""Unit tests for the registry: building, enumeration, lookup, filtering, integrity."""

from __future__ import annotations

from typing import Any

import pytest

from synthaudit_bench import registry as reg


def _rec(
    dataset_id: str,
    *,
    stratum: str = "census",
    domain: str = "energy",
    family: str = "physics-simulator",
    task: str = "classification",
    license_name: str = "CC BY 4.0",
    gen_version: str | None = None,
    transparency: dict[str, bool] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": dataset_id,
        "title": dataset_id.title(),
        "frame_stratum": stratum,
        "domain": domain,
        "generator_family": family,
        "provenance_confidence": "documented",
        "modality": "tabular",
        "task": task,
        "target": "y",
        "license": {"name": license_name, "redistribute": True, "fetch_scriptable": True},
        "source": {
            "urls": ["https://example.org/x.csv"],
            "sha256": {"x.csv": "a" * 64},
            "retrieved": "2026-07-23",
        },
        "loader": {"format": "csv"},
        "transparency": transparency
        or {
            "generator_described": True,
            "generator_code_available": False,
            "seed_reported": True,
            "artifacts_disclosed": False,
        },
        "citation": "Example 2026",
    }
    if gen_version is not None:
        record["generator_version"] = gen_version
    return record


def _registry() -> reg.Registry:
    records = [
        (_rec("grid", family="physics-simulator"), "census"),
        (_rec("adult", domain="finance", family="gan", gen_version="0.10.0"), "census"),
        (
            _rec("planted-1", stratum="planted", family="rule-based", task="regression"),
            "evaluation",
        ),
        (_rec("ctrl-1", stratum="controlled", domain="finance", family="gan"), "evaluation"),
    ]
    splits = {"planted-1": "public-dev", "ctrl-1": "held-out"}
    manifest = {"grid": "h" * 64, "planted-1": "g" * 64}
    return reg.build_registry(records, splits=splits, manifest=manifest)


# --- loading and ordering -------------------------------------------------------


def test_build_orders_by_corpus_then_id() -> None:
    r = _registry()
    assert [e.id for e in r] == ["adult", "grid", "ctrl-1", "planted-1"]
    assert r.ids() == ("adult", "ctrl-1", "grid", "planted-1")
    assert len(r) == 4


def test_ordering_is_deterministic_under_input_shuffling() -> None:
    records = [(_rec(i), "census") for i in ("c", "a", "b")]
    first = reg.build_registry(records)
    second = reg.build_registry(list(reversed(records)))
    assert [e.id for e in first] == [e.id for e in second] == ["a", "b", "c"]
    assert first.index.to_mapping() == second.index.to_mapping()


def test_entry_and_index_serialization() -> None:
    r = _registry()
    grid = r.get("grid")
    assert grid.to_mapping()["corpus"] == "census"
    assert grid.to_mapping()["content_hash"] == "h" * 64
    assert "split" not in grid.to_mapping()
    assert r.get("planted-1").to_mapping()["split"] == "public-dev"
    index = r.index.to_mapping()
    assert index["by_corpus"]["census"] == ["adult", "grid"]
    assert index["by_version"] == {"0.10.0": ["adult"]}
    assert index["by_content_hash"] == {"g" * 64: "planted-1", "h" * 64: "grid"}


# --- schema validation, duplicates, missing metadata ----------------------------


def test_schema_invalid_record_raises() -> None:
    bad = _rec("x")
    del bad["title"]  # required field
    with pytest.raises(reg.InvalidRecordError, match="schema validation"):
        reg.build_registry([(bad, "census")])


def test_missing_required_object_raises() -> None:
    bad = _rec("x")
    del bad["license"]
    with pytest.raises(reg.InvalidRecordError):
        reg.build_registry([(bad, "census")])


def test_invalid_enum_value_raises() -> None:
    with pytest.raises(reg.InvalidRecordError, match="invalid field"):
        reg.build_registry([(_rec("x", family="not-a-family"), "census")])


def test_duplicate_id_raises() -> None:
    with pytest.raises(reg.DuplicateIdError, match="duplicate"):
        reg.build_registry([(_rec("dup"), "census"), (_rec("dup", domain="x"), "census")])


def test_orphan_split_and_manifest_raise() -> None:
    with pytest.raises(reg.IntegrityError, match="splits reference unknown"):
        reg.build_registry([(_rec("a"), "evaluation")], splits={"ghost": "public-dev"})
    with pytest.raises(reg.IntegrityError, match="manifest reference"):
        reg.build_registry([(_rec("a"), "census")], manifest={"ghost": "h" * 64})


def test_invalid_split_value_raises() -> None:
    with pytest.raises(reg.RegistryError, match="invalid split"):
        reg.build_registry([(_rec("a"), "evaluation")], splits={"a": "weird"})


# --- enumeration ----------------------------------------------------------------


def test_enumeration_axes() -> None:
    r = _registry()
    assert [e.id for e in reg.enumerate_corpus(r, "census")] == ["adult", "grid"]
    assert [e.id for e in r.by_split("public-dev")] == ["planted-1"]
    assert [e.id for e in r.by_generator_family("gan")] == ["adult", "ctrl-1"]
    assert [e.id for e in r.by_domain("finance")] == ["adult", "ctrl-1"]
    assert [e.id for e in r.by_task("regression")] == ["planted-1"]
    assert [e.id for e in r.by_modality("tabular")] == ["adult", "ctrl-1", "grid", "planted-1"]
    assert [e.id for e in r.by_license("CC BY 4.0")] == ["adult", "ctrl-1", "grid", "planted-1"]
    assert [e.id for e in r.by_provenance_confidence("documented")] == [
        "adult",
        "ctrl-1",
        "grid",
        "planted-1",
    ]
    assert [e.id for e in r.by_transparency(seed_reported=True, artifacts_disclosed=False)] == [
        "adult",
        "ctrl-1",
        "grid",
        "planted-1",
    ]


def test_list_datasets_with_corpus_and_split() -> None:
    r = _registry()
    assert [e.id for e in reg.list_datasets(r)] == ["adult", "ctrl-1", "grid", "planted-1"]
    assert [e.id for e in reg.list_datasets(r, corpus="evaluation")] == ["ctrl-1", "planted-1"]
    assert [e.id for e in reg.list_datasets(r, corpus="evaluation", split="held-out")] == ["ctrl-1"]


# --- lookup and filtering -------------------------------------------------------


def test_lookup() -> None:
    r = _registry()
    assert reg.get_dataset(r, "grid").corpus is reg.Corpus.CENSUS
    assert r.contains("grid") is True
    assert r.contains("ghost") is False
    with pytest.raises(reg.UnknownDatasetError, match="unknown dataset"):
        reg.get_dataset(r, "ghost")


def test_filter_registry_combines_criteria() -> None:
    r = _registry()
    assert [e.id for e in reg.filter_registry(r, domain="finance", generator_family="gan")] == [
        "adult",
        "ctrl-1",
    ]
    assert [e.id for e in reg.filter_registry(r, corpus="evaluation", split="public-dev")] == [
        "planted-1"
    ]
    assert [
        e.id
        for e in reg.filter_registry(r, task="classification", transparency={"seed_reported": True})
    ] == ["adult", "ctrl-1", "grid"]
    assert reg.registry_index(r) is r.index


def test_registry_filter_predicate() -> None:
    r = _registry()
    assert [e.id for e in r.filter(lambda e: e.record.domain == "finance")] == ["adult", "ctrl-1"]


# --- referential integrity ------------------------------------------------------


def test_integrity_clean() -> None:
    report = reg.referential_integrity(_registry())
    assert report.ok is True
    assert report.to_mapping() == {"ok": True, "issues": []}


def test_integrity_detects_corpus_stratum_and_split_problems() -> None:
    records = [
        (_rec("bad-census", stratum="planted"), "census"),  # census must be census stratum
        (_rec("eval-nosplit", stratum="planted"), "evaluation"),  # evaluation needs a split
    ]
    report = reg.referential_integrity(reg.build_registry(records))
    codes = sorted({issue.code for issue in report.issues})
    assert codes == ["corpus_stratum_mismatch", "missing_split"]


def test_integrity_detects_unexpected_split_and_duplicate_hash() -> None:
    records = [(_rec("a"), "census"), (_rec("b"), "census")]
    r = reg.build_registry(
        records, splits={"a": "public-dev"}, manifest={"a": "h" * 64, "b": "h" * 64}
    )
    codes = sorted({issue.code for issue in reg.referential_integrity(r).issues})
    assert codes == ["duplicate_content_hash", "unexpected_split"]


def test_integrity_version_compatibility() -> None:
    r = _registry()
    ok = reg.referential_integrity(r, sto_version="1.0.0", schema_version="1.0.0")
    assert ok.ok is True
    bad = reg.referential_integrity(r, sto_version="9.9.9", schema_version="2.0.0")
    assert sorted(i.code for i in bad.issues) == [
        "unavailable_sto_version",
        "unsupported_schema_version",
    ]
    # a malformed requested version is treated as unsupported, not an exception
    assert reg.referential_integrity(r, schema_version="not-a-version").issues[0].code == (
        "unsupported_schema_version"
    )


def test_validate_registry_raises_on_integrity_failure() -> None:
    r = reg.build_registry([(_rec("eval-nosplit", stratum="planted"), "evaluation")])
    with pytest.raises(reg.IntegrityError, match="referential integrity"):
        reg.validate_registry(r)
    assert reg.validate_registry(_registry()) is not None

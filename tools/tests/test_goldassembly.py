"""Tests for gold assembly."""

from __future__ import annotations

from typing import Any

import pytest
from benchkit.errors import ValidationError
from benchkit.goldassembly import assemble_gold, gold_files
from synthaudit_bench import schemas

from _fixtures import annotation_entry


def _reconciled(**kwargs: Any) -> dict[str, Any]:
    return annotation_entry(gold_type="adjudicated", **kwargs)


def test_assemble_produces_gold_tuples() -> None:
    assembly = assemble_gold([_reconciled(dataset_id="fx-1")])
    assert assembly.n_tuples == 1
    assert "fx-1" in assembly.by_dataset


def test_gold_files_validate_against_frozen_schema() -> None:
    assembly = assemble_gold([_reconciled(dataset_id="fx-1")])
    for tuples in gold_files(assembly).values():
        for mapping in tuples:
            schemas.validate_instance("gold-tuple", mapping)


def test_missing_gold_type_fails_closed() -> None:
    # A raw form entry (no gold_type) must not be silently defaulted.
    with pytest.raises(ValidationError):
        assemble_gold([annotation_entry()])


def test_invalid_entry_fails_closed() -> None:
    with pytest.raises(ValidationError):
        assemble_gold([_reconciled(disposition="bogus")])


def test_absent_entries_are_not_assembled() -> None:
    assembly = assemble_gold([_reconciled(present="no")])
    assert assembly.n_tuples == 0


def test_assembly_is_deterministic() -> None:
    entries = [_reconciled(dataset_id="fx-2"), _reconciled(dataset_id="fx-1", support="col_b")]
    first = gold_files(assemble_gold(entries))
    second = gold_files(assemble_gold(list(reversed(entries))))
    assert first == second

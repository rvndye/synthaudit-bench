"""Structural-consistency tests for ``Ontology.from_mapping``.

These exercise the checks the JSON Schema cannot express, by mutating deep copies
of the canonical register.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from synthaudit_bench.errors import OntologyError
from synthaudit_bench.sto import Ontology


def test_valid_register_builds(sto_register: dict[str, Any]) -> None:
    onto = Ontology.from_mapping(sto_register)
    assert len(onto.class_ids) == 16


def test_duplicate_class_id_rejected(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["classes"][1]["id"] = data["classes"][0]["id"]
    with pytest.raises(OntologyError, match="duplicate"):
        Ontology.from_mapping(data)


def test_unknown_relationship_reference_rejected(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["classes"][0]["relationships"] = ["generalizes STO-Z99"]
    with pytest.raises(OntologyError, match="unknown class"):
        Ontology.from_mapping(data)


def test_incomplete_role_precedence_rejected(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["role_precedence"] = data["role_precedence"][:-1]
    with pytest.raises(OntologyError, match="role_precedence"):
        Ontology.from_mapping(data)


def test_deprecation_replaced_by_unknown_rejected(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["classes"][0]["deprecation"] = {
        "since_version": "2.0.0",
        "replaced_by": "STO-Z99",
        "reason": "test",
    }
    with pytest.raises(OntologyError, match="replaced_by"):
        Ontology.from_mapping(data)

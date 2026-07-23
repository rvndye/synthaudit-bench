"""Deprecation-support tests.

STO v1.0 deprecates no class, so deprecation is exercised through fixtures built
from copies of the register.
"""

from __future__ import annotations

import copy
from typing import Any

from synthaudit_bench import sto
from synthaudit_bench.sto import Ontology


def test_no_v1_class_is_deprecated() -> None:
    onto = sto.load()
    assert all(not onto.is_deprecated(cid) for cid in onto.class_ids)


def test_deprecated_class_is_reported(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["classes"][0]["deprecation"] = {
        "since_version": "2.0.0",
        "replaced_by": "STO-A02",
        "reason": "merged into the balance class",
    }
    onto = Ontology.from_mapping(data)
    cid = data["classes"][0]["id"]
    assert onto.is_deprecated(cid) is True
    assert onto.replacement(cid) == "STO-A02"


def test_deprecated_class_with_null_replacement(sto_register: dict[str, Any]) -> None:
    data = copy.deepcopy(sto_register)
    data["classes"][0]["deprecation"] = {
        "since_version": "2.0.0",
        "replaced_by": None,
        "reason": "withdrawn",
    }
    onto = Ontology.from_mapping(data)
    cid = data["classes"][0]["id"]
    assert onto.is_deprecated(cid) is True
    assert onto.replacement(cid) is None


def test_non_deprecated_class_has_no_replacement(sto_register: dict[str, Any]) -> None:
    onto = Ontology.from_mapping(sto_register)
    assert onto.is_deprecated("STO-A01") is False
    assert onto.replacement("STO-A01") is None

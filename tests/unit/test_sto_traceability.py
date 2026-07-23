"""Tests for the STO-to-SynthAudit traceability map (issue 1.3)."""

from __future__ import annotations

from typing import Any

import pytest

from synthaudit_bench import sto
from synthaudit_bench.errors import OntologyError
from synthaudit_bench.sto import Ontology


def test_every_class_has_a_traceability_entry() -> None:
    onto = sto.load()
    for cid in onto.class_ids:
        field = onto.traceability_for(cid)
        assert field is not None and field.strip()


def test_traceability_spot_check() -> None:
    onto = sto.load()
    assert onto.traceability_for("STO-A03") == "results.identity.identities[type=power_law]"
    assert onto.traceability_for("STO-R02") == "results.leakage.train_test_overlap_rows"


def test_traceability_for_unknown_class_is_none() -> None:
    assert sto.load().traceability_for("STO-Z99") is None


def test_incomplete_traceability_is_rejected(sto_register: dict[str, Any]) -> None:
    partial = {"STO-A01": "results.identity.identities[type=linear]"}
    onto = Ontology.from_mapping(sto_register, partial)
    with pytest.raises(OntologyError, match="incomplete"):
        sto._require_complete_traceability(onto)

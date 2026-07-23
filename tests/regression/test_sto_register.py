"""Regression snapshot of the STO v1.0 register.

These freeze the observable shape of the ontology so that any accidental change
to the register (ids, ordering, gold types, dispositions, role precedence) fails
loudly. Intentional changes update this snapshot together with a version bump.
"""

from __future__ import annotations

from synthaudit_bench import sto
from synthaudit_bench.model import Version

EXPECTED_IDS = (
    "STO-A01",
    "STO-A02",
    "STO-A03",
    "STO-A04",
    "STO-A05",
    "STO-A06",
    "STO-A07",
    "STO-A08",
    "STO-S01",
    "STO-S02",
    "STO-S03",
    "STO-S04",
    "STO-R01",
    "STO-R02",
    "STO-P01",
    "STO-D01",
)
EXPECTED_ADJUDICATED = {"STO-A06", "STO-P01", "STO-D01"}
EXPECTED_ROLE_PRECEDENCE = (
    "target",
    "constant",
    "identifier",
    "datetime",
    "duplicate",
    "label_component",
    "derived_deterministic",
    "leaky_feature",
    "near_deterministic",
    "no_signal",
    "input",
)


def test_register_ids_are_frozen() -> None:
    assert sto.load().class_ids == EXPECTED_IDS


def test_version_is_pinned() -> None:
    assert sto.load().version == Version(1, 0, 0)


def test_adjudicated_classes_are_frozen() -> None:
    onto = sto.load()
    adjudicated = {cid for cid in onto.class_ids if not onto.is_objective(cid)}
    assert adjudicated == EXPECTED_ADJUDICATED


def test_role_precedence_is_frozen() -> None:
    precedence = tuple(role.value for role in sto.load().role_precedence)
    assert precedence == EXPECTED_ROLE_PRECEDENCE


def test_dispositions_are_frozen() -> None:
    labels = {disposition.value for disposition in sto.load().dispositions}
    assert labels == {
        "target_leakage",
        "structural_constraint",
        "redundancy",
        "not_applicable",
    }

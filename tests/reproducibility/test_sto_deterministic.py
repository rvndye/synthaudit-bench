"""Deterministic-loading tests for the ontology.

Loading the same ontology version must always yield an equal object, and the
class ordering must be stable across loads.
"""

from __future__ import annotations

from synthaudit_bench import sto


def test_load_is_cached() -> None:
    assert sto.load() is sto.load()


def test_reload_yields_equal_ontology() -> None:
    first = sto.load()
    sto.load.cache_clear()
    second = sto.load()
    assert second is not first
    assert second == first


def test_class_order_is_stable_across_reloads() -> None:
    sto.load.cache_clear()
    first = sto.load().class_ids
    sto.load.cache_clear()
    second = sto.load().class_ids
    assert first == second

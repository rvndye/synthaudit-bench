"""Tests for the corpus builder."""

from __future__ import annotations

from benchkit.corpus import DesignSpec, PoolItem, plan_corpus, pool_from_census


def _pool(n: int, *, group_size: int = 1) -> list[PoolItem]:
    items: list[PoolItem] = []
    for i in range(n):
        group = f"g{i // group_size}"
        items.append(PoolItem(id=f"item-{i:03d}", axes={"generator_family": "gan"}, group=group))
    return items


def test_empty_pool_yields_empty_plan() -> None:
    plan = plan_corpus([], DesignSpec())
    assert plan.items == ()
    assert plan.leakage_ok


def test_plan_is_deterministic() -> None:
    pool = _pool(20)
    spec = DesignSpec(root_seed=42, held_out_fraction=0.3)
    assert (
        plan_corpus(pool, spec).to_mapping() == plan_corpus(list(reversed(pool)), spec).to_mapping()
    )


def test_held_out_fraction_zero_keeps_all_public() -> None:
    plan = plan_corpus(_pool(30), DesignSpec(held_out_fraction=0.0))
    assert plan.splits()["held-out"] == []
    assert len(plan.splits()["public-dev"]) == 30


def test_held_out_fraction_one_moves_all() -> None:
    plan = plan_corpus(_pool(30), DesignSpec(held_out_fraction=1.0))
    assert plan.splits()["public-dev"] == []
    assert len(plan.splits()["held-out"]) == 30


def test_grouping_prevents_leakage() -> None:
    # 10 groups of 3 items each; every group must land entirely in one split.
    plan = plan_corpus(_pool(30, group_size=3), DesignSpec(held_out_fraction=0.5))
    assert plan.leakage_ok
    split_of: dict[str, str] = {}
    for item in plan.items:
        split_of.setdefault(item.group, item.split)
        assert split_of[item.group] == item.split


def test_select_limit_caps_selection() -> None:
    plan = plan_corpus(_pool(50), DesignSpec(select_limit=10))
    assert len(plan.items) == 10


def test_balance_targets_respected() -> None:
    pool = [PoolItem(id=f"g-{i}", axes={"generator_family": "gan"}) for i in range(5)] + [
        PoolItem(id=f"v-{i}", axes={"generator_family": "vae"}) for i in range(5)
    ]
    spec = DesignSpec(balance_key="generator_family", per_value_target={"gan": 2, "vae": 3})
    plan = plan_corpus(pool, spec)
    families = [item.axis_value for item in plan.items]
    assert families.count("gan") == 2
    assert families.count("vae") == 3


def test_pool_from_census_reads_declared_group() -> None:
    census = [{"id": "x", "declared": {"generator_family": "gan", "base_group": "base-1"}}]
    pool = pool_from_census(census)
    assert pool[0].group == "base-1"
    assert pool[0].axes["generator_family"] == "gan"

"""Deliverable 3: corpus builder.

The machinery that plans an evaluation corpus over a *provided* candidate pool
according to the published Corpus Protocol: deterministic seeded selection,
metadata balancing, held-out split creation, and leakage prevention. It produces a
plan (which candidates are selected and how they are split), never datasets and
never gold: it creates no benchmark content. With an empty pool it produces an empty
plan.

Determinism comes from the frozen ``derive_seed``: selection order and held-out
assignment are functions of the root seed and stable ids only, so the plan is
reproducible and independent of input order. Leakage is prevented by assigning an
entire base group (for example, all synthetic tables sharing one base table) to the
same split, so no group can straddle public-dev and held-out.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from synthaudit_bench.runner.plan import derive_seed

from benchkit.errors import ValidationError
from benchkit.provenance import provenance_block

__all__ = ["CorpusPlan", "DesignSpec", "PlanItem", "PoolItem", "plan_corpus", "pool_from_census"]

_SEED_SPACE = 2**32


@dataclass(frozen=True, slots=True)
class PoolItem:
    """One candidate available to the planner (identity plus balancing metadata)."""

    id: str
    axes: Mapping[str, str] = field(default_factory=dict)
    group: str | None = None


@dataclass(frozen=True, slots=True)
class DesignSpec:
    """A corpus design: seed, held-out fraction, and optional balancing targets."""

    root_seed: int = 42
    held_out_fraction: float = 0.0
    balance_key: str | None = None
    per_value_target: Mapping[str, int] | None = None
    select_limit: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.held_out_fraction <= 1.0:
            raise ValidationError("held_out_fraction must be in [0, 1]")
        if self.select_limit is not None and self.select_limit < 0:
            raise ValidationError("select_limit must be non-negative")


@dataclass(frozen=True, slots=True)
class PlanItem:
    """One selected candidate with its split assignment."""

    id: str
    split: str  # "public-dev" | "held-out"
    group: str
    axis_value: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this plan item."""
        mapping: dict[str, Any] = {"id": self.id, "split": self.split, "group": self.group}
        if self.axis_value is not None:
            mapping["axis_value"] = self.axis_value
        return mapping


@dataclass(frozen=True, slots=True)
class CorpusPlan:
    """A deterministic corpus plan over a provided pool. Creates no content."""

    items: tuple[PlanItem, ...]
    balance: dict[str, dict[str, int]]
    leakage_ok: bool
    provenance: dict[str, Any]

    def splits(self) -> dict[str, list[str]]:
        """Return the public-dev and held-out id lists (the shape of splits.json)."""
        out: dict[str, list[str]] = {"public-dev": [], "held-out": []}
        for item in self.items:
            out[item.split].append(item.id)
        return {key: sorted(values) for key, values in out.items()}

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the plan."""
        return {
            "n_selected": len(self.items),
            "leakage_ok": self.leakage_ok,
            "splits": self.splits(),
            "balance": self.balance,
            "items": [item.to_mapping() for item in self.items],
            "provenance": self.provenance,
        }


def pool_from_census(
    census_records: Iterable[Mapping[str, Any]],
    *,
    group_field: str = "base_group",
) -> list[PoolItem]:
    """Build pool items from census record mappings (reads declared metadata only)."""
    items: list[PoolItem] = []
    for record in census_records:
        declared = record.get("declared", {})
        group = declared.get(group_field)
        items.append(
            PoolItem(id=str(record["id"]), axes=dict(declared), group=group if group else None)
        )
    return items


def _ordering_key(spec: DesignSpec, item: PoolItem) -> tuple[int, str]:
    return (derive_seed(spec.root_seed, item.id), item.id)


def _select(items: list[PoolItem], spec: DesignSpec) -> list[PoolItem]:
    ordered = sorted(items, key=lambda it: _ordering_key(spec, it))
    if spec.balance_key is None and spec.select_limit is None:
        return ordered
    selected: list[PoolItem] = []
    per_value: dict[str, int] = {}
    for item in ordered:
        if spec.select_limit is not None and len(selected) >= spec.select_limit:
            break
        if spec.balance_key is not None and spec.per_value_target is not None:
            value = str(item.axes.get(spec.balance_key, ""))
            target = spec.per_value_target.get(value)
            if target is not None and per_value.get(value, 0) >= target:
                continue
            per_value[value] = per_value.get(value, 0) + 1
        selected.append(item)
    return selected


def _group_key(item: PoolItem) -> str:
    return item.group if item.group is not None else item.id


def _assign_splits(selected: list[PoolItem], spec: DesignSpec) -> dict[str, str]:
    """Assign each group to a split deterministically; all items in a group agree."""
    group_split: dict[str, str] = {}
    for group in sorted({_group_key(item) for item in selected}):
        value = derive_seed(spec.root_seed, f"holdout:{group}") / _SEED_SPACE
        group_split[group] = "held-out" if value < spec.held_out_fraction else "public-dev"
    return group_split


def plan_corpus(pool: Iterable[PoolItem], spec: DesignSpec) -> CorpusPlan:
    """Return a deterministic corpus plan for ``pool`` under ``spec``.

    Selection is seeded and (optionally) balanced to per-value targets; split
    assignment is per base group so no group straddles the split (leakage
    prevention). The plan selects from the provided pool only and produces no
    datasets or gold.
    """
    items = list(pool)
    selected = _select(items, spec)
    group_split = _assign_splits(selected, spec)

    plan_items: list[PlanItem] = []
    for item in sorted(selected, key=lambda it: it.id):
        group = _group_key(item)
        axis_value = item.axes.get(spec.balance_key) if spec.balance_key else None
        plan_items.append(PlanItem(item.id, group_split[group], group, axis_value))

    # Leakage invariant: a group must never appear in two splits.
    seen: dict[str, str] = {}
    leakage_ok = True
    for plan_item in plan_items:
        prior = seen.setdefault(plan_item.group, plan_item.split)
        if prior != plan_item.split:
            leakage_ok = False
    if not leakage_ok:  # pragma: no cover - guarded by construction, defensive only
        raise ValidationError("internal leakage: a base group spans two splits")

    balance: dict[str, dict[str, int]] = {"public-dev": {}, "held-out": {}}
    if spec.balance_key is not None:
        for plan_item in plan_items:
            value = str(plan_item.axis_value or "")
            balance[plan_item.split][value] = balance[plan_item.split].get(value, 0) + 1

    provenance = provenance_block(
        tool="corpus.plan",
        inputs=[item.id for item in selected],
        parameters={
            "root_seed": spec.root_seed,
            "held_out_fraction": spec.held_out_fraction,
            "balance_key": spec.balance_key or "",
            "select_limit": spec.select_limit if spec.select_limit is not None else -1,
        },
    )
    return CorpusPlan(tuple(plan_items), balance, leakage_ok, provenance)

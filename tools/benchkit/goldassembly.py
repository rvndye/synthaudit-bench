"""Deliverable 7: gold assembly.

Converts completed, reconciled adjudicated annotations into frozen gold-tuple objects
and gold release artifacts, with a validation report. It consumes only completed
annotations and never infers a missing value: if an entry is incomplete or invalid,
assembly fails closed rather than filling anything in. It emits gold files in the
exact shape the frozen scorer loads (``evaluation/gold/<id>.json``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from synthaudit_bench.gold import validate_gold
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ROWS, TABLE, GoldTuple, Support

from benchkit.errors import ValidationError
from benchkit.provenance import provenance_block
from benchkit.validation import canonical_support, parse_present, validate_annotations

__all__ = ["GoldAssembly", "assemble_gold", "gold_files"]


@dataclass(frozen=True, slots=True)
class GoldAssembly:
    """Assembled gold, grouped by dataset. Contains only what the annotations stated."""

    by_dataset: dict[str, tuple[GoldTuple, ...]]
    provenance: dict[str, Any]

    @property
    def n_tuples(self) -> int:
        """Total gold tuples assembled."""
        return sum(len(tuples) for tuples in self.by_dataset.values())


def _support_value(raw: Any) -> Support:
    kind, canon = canonical_support(raw)
    if kind == "rows":
        return ROWS
    if kind == "table":
        return TABLE
    return frozenset(canon.split("|"))


def _tuple_from_entry(entry: Mapping[str, Any]) -> GoldTuple:
    disposition = str(entry.get("disposition", "")).strip()
    gold_type = str(entry.get("gold_type", "")).strip()
    class_id = str(entry.get("candidate_class", "")).strip()
    evidence = str(entry.get("evidence", "")).strip()
    # Never infer: a missing gold_type or disposition is an error, not a default.
    if not gold_type:
        raise ValidationError(
            f"entry for {entry.get('dataset_id')!r}/{class_id}: missing gold_type"
        )
    return GoldTuple(
        support=_support_value(entry.get("support")),
        classes=frozenset({class_id}),
        dispositions=frozenset({Disposition(disposition)}),
        gold_type=GoldType(gold_type),
        optional=bool(entry.get("optional", False)),
        evidence=evidence or None,
    )


def assemble_gold(
    entries: Iterable[Mapping[str, Any]],
    *,
    sto_version: str = "1.0.0",
    generated_at: str | None = None,
) -> GoldAssembly:
    """Assemble gold from reconciled annotation ``entries`` (fails closed).

    Entries must carry ``gold_type`` (this is the reconciled output, not a raw form)
    and must pass annotation validation. Only entries marked present are assembled;
    each becomes exactly one gold tuple. Nothing is inferred. Raises on any invalid or
    incomplete entry.
    """
    rows = [entry for entry in entries if parse_present(entry.get("present"))]
    report = validate_annotations(rows, sto_version=sto_version)
    if not report.ok:
        raise ValidationError(
            f"cannot assemble gold: {len(report.issues)} validation issue(s); "
            f"first: {report.issues[0].message}"
        )

    by_dataset: dict[str, list[GoldTuple]] = {}
    for entry in rows:
        did = str(entry["dataset_id"])
        by_dataset.setdefault(did, []).append(_tuple_from_entry(entry))

    finalized: dict[str, tuple[GoldTuple, ...]] = {}
    for did in sorted(by_dataset):
        tuples = tuple(by_dataset[did])
        validate_gold(tuples, sto_version=sto_version)  # frozen semantic validation, fail closed
        finalized[did] = tuples

    provenance = provenance_block(
        tool="gold.assemble",
        inputs=sorted(finalized),
        parameters={"sto_version": sto_version, "n_entries": len(rows)},
        generated_at=generated_at,
    )
    return GoldAssembly(by_dataset=finalized, provenance=provenance)


def gold_files(assembly: GoldAssembly) -> dict[str, list[dict[str, Any]]]:
    """Return ``dataset_id -> [gold tuple mapping]`` ready to write as gold/<id>.json."""
    return {
        did: [gold_tuple.to_mapping() for gold_tuple in tuples]
        for did, tuples in sorted(assembly.by_dataset.items())
    }

"""Deliverable 5: annotation validation.

Validators over completed annotation entries: completeness, schema compliance
(against the frozen gold-tuple schema), support canonicalization, disposition
validity, and duplicate detection. It validates only; it never fixes, infers, or
fills a value. Any problem is reported; the report's ``ok`` is false if any entry is
invalid, so a caller fails closed.

An annotation entry is a mapping with the fields the annotation form declares:
``dataset_id``, ``annotator_id``, ``support``, ``candidate_class``, ``disposition``,
``present``, ``confidence`` (optional), ``evidence``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.tuples import ROWS, TABLE
from synthaudit_bench.schemas.errors import SchemaValidationError
from synthaudit_bench.sto import load as load_ontology

from benchkit.provenance import provenance_block

__all__ = [
    "Issue",
    "ValidationReport",
    "canonical_support",
    "parse_present",
    "validate_annotations",
]

_REQUIRED = ("dataset_id", "annotator_id", "support", "candidate_class", "disposition", "present")
_TRUE = {"yes", "true", "1", "y", "present"}
_FALSE = {"no", "false", "0", "n", "absent"}


@dataclass(frozen=True, slots=True)
class Issue:
    """One validation problem, anchored to an entry."""

    index: int
    dataset_id: str
    annotator_id: str
    field: str
    message: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this issue."""
        return {
            "index": self.index,
            "dataset_id": self.dataset_id,
            "annotator_id": self.annotator_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The outcome of validating an annotation set."""

    n_entries: int
    issues: tuple[Issue, ...]
    provenance: dict[str, Any]

    @property
    def ok(self) -> bool:
        """True when there are no issues."""
        return not self.issues

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the report."""
        return {
            "ok": self.ok,
            "n_entries": self.n_entries,
            "n_issues": len(self.issues),
            "issues": [issue.to_mapping() for issue in self.issues],
            "provenance": self.provenance,
        }


def parse_present(value: Any) -> bool | None:
    """Parse a present/absent flag to a bool, or None when it is malformed."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def canonical_support(raw: Any) -> tuple[str, str]:
    """Return ``(kind, canonical)`` for a support value, or raise ValueError.

    ``kind`` is ``rows``, ``table``, or ``columns``. For columns, ``canonical`` is
    the pipe-joined sorted unique column set. Reserved tokens must appear alone.
    """
    if isinstance(raw, str) and raw in (ROWS, TABLE):
        return ("rows" if raw == ROWS else "table", raw)
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(",", "|").split("|")]
    elif isinstance(raw, (list, tuple)):
        parts = [str(p).strip() for p in raw]
    else:
        raise ValueError(f"support must be a string or list, got {type(raw).__name__}")
    columns = [p for p in parts if p]
    if not columns:
        raise ValueError("support is empty")
    if any(token in (ROWS, TABLE) for token in columns):
        raise ValueError("reserved support token must appear alone")
    unique = sorted(set(columns))
    return ("columns", "|".join(unique))


def _gold_type_for(class_id: str, sto_version: str) -> str | None:
    ontology = load_ontology(sto_version)
    for class_def in ontology.classes.values():
        if class_def.id == class_id:
            gold_type = getattr(class_def, "gold_type", None)
            return str(getattr(gold_type, "value", gold_type))
    return None


def validate_annotations(
    entries: Iterable[Mapping[str, Any]],
    *,
    sto_version: str = "1.0.0",
    generated_at: str | None = None,
) -> ValidationReport:
    """Validate annotation ``entries`` and return a structured report (fail closed)."""
    dispositions = {d.value for d in Disposition}
    issues: list[Issue] = []
    seen: dict[tuple[str, str, str, str], int] = {}
    rows = list(entries)

    for index, entry in enumerate(rows):
        did = str(entry.get("dataset_id", ""))
        aid = str(entry.get("annotator_id", ""))

        def add(
            field: str, message: str, _idx: int = index, _did: str = did, _aid: str = aid
        ) -> None:
            issues.append(Issue(_idx, _did, _aid, field, message))

        for field in _REQUIRED:
            if not str(entry.get(field, "")).strip():
                add(field, "required field is missing or empty")

        present = parse_present(entry.get("present"))
        if present is None:
            add("present", f"not a present/absent flag: {entry.get('present')!r}")

        disposition = str(entry.get("disposition", "")).strip()
        if disposition and disposition not in dispositions:
            add(
                "disposition",
                f"invalid disposition {disposition!r} (allowed: {sorted(dispositions)})",
            )

        class_id = str(entry.get("candidate_class", "")).strip()
        gold_type = _gold_type_for(class_id, sto_version) if class_id else None
        if class_id and gold_type is None:
            add("candidate_class", f"unknown STO class {class_id!r}")

        canon: str | None = None
        canon_kind: str | None = None
        try:
            canon_kind, canon = canonical_support(entry.get("support"))
        except ValueError as exc:
            add("support", str(exc))

        # Present items must be schema-valid gold tuples and evidence-bearing.
        if present and canon is not None and gold_type is not None and disposition in dispositions:
            if not str(entry.get("evidence", "")).strip():
                add("evidence", "a present artifact requires evidence")
            support_value: Any = canon if canon_kind in ("rows", "table") else canon.split("|")
            tuple_mapping = {
                "support": support_value,
                "classes": [class_id],
                "dispositions": [disposition],
                "gold_type": gold_type,
                "evidence": str(entry.get("evidence", "")),
            }
            try:
                schemas.validate_instance("gold-tuple", tuple_mapping)
            except SchemaValidationError as exc:
                add("schema", f"proposed gold tuple invalid: {exc}")

            key = (aid, did, canon, class_id)
            if key in seen:
                add(
                    "duplicate",
                    f"duplicate of entry {seen[key]} (same annotator, dataset, support, class)",
                )
            else:
                seen[key] = index

    issues.sort(key=lambda i: (i.index, i.field))
    provenance = provenance_block(
        tool="annotation.validate",
        parameters={"sto_version": sto_version, "n_entries": len(rows)},
        generated_at=generated_at,
    )
    return ValidationReport(n_entries=len(rows), issues=tuple(issues), provenance=provenance)

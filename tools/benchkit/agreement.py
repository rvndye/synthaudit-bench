"""Deliverable 6: agreement analysis.

Reproducible computation of inter-annotator agreement between two annotators over the
same datasets: Cohen's kappa on class presence and on disposition, raw class and
disposition agreement, a disagreement summary, and an adjudication report listing
what must be reconciled. It computes statistics only; it generates no gold and makes
no label decision.

The item universe is the union of candidate loci ``(dataset_id, canonical_support)``
raised by either annotator. At each locus an annotator's class label is the class
they assigned there, or ``NONE`` if they did not raise it, so kappa reflects
agreement on what class (if any) sits at each raised locus.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from benchkit.errors import InputError
from benchkit.provenance import provenance_block
from benchkit.validation import canonical_support, parse_present

__all__ = ["AgreementReport", "analyze_agreement", "cohen_kappa"]

_NONE = "NONE"


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Return Cohen's kappa for two aligned label sequences.

    When chance agreement is total (a single category), kappa is 1.0 if the labels
    agree everywhere and 0.0 otherwise, the standard degenerate-case convention.
    """
    if len(labels_a) != len(labels_b):
        raise InputError("label sequences must be the same length")
    n = len(labels_a)
    if n == 0:
        return 1.0
    observed = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b) / n
    categories = set(labels_a) | set(labels_b)
    count_a = {c: labels_a.count(c) / n for c in categories}
    count_b = {c: labels_b.count(c) / n for c in categories}
    expected = sum(count_a[c] * count_b[c] for c in categories)
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def _present_index(entries: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], tuple[str, str]]:
    """Map each present locus (dataset_id, canonical_support) to (class, disposition)."""
    index: dict[tuple[str, str], tuple[str, str]] = {}
    for entry in entries:
        if not parse_present(entry.get("present")):
            continue
        try:
            _, canon = canonical_support(entry.get("support"))
        except ValueError:
            continue
        did = str(entry.get("dataset_id", ""))
        cls = str(entry.get("candidate_class", "")).strip()
        disp = str(entry.get("disposition", "")).strip()
        index[(did, canon)] = (cls, disp)
    return index


@dataclass(frozen=True, slots=True)
class AgreementReport:
    """The agreement analysis between two annotators."""

    annotator_a: str
    annotator_b: str
    n_items: int
    class_kappa: float
    disposition_kappa: float
    class_agreement: float
    disposition_agreement: float
    disagreements: tuple[dict[str, Any], ...]
    provenance: dict[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the report."""
        return {
            "annotator_a": self.annotator_a,
            "annotator_b": self.annotator_b,
            "n_items": self.n_items,
            "class_kappa": self.class_kappa,
            "disposition_kappa": self.disposition_kappa,
            "class_agreement": self.class_agreement,
            "disposition_agreement": self.disposition_agreement,
            "n_disagreements": len(self.disagreements),
            "disagreements": list(self.disagreements),
            "provenance": self.provenance,
        }


def analyze_agreement(
    annotator_a: str,
    entries_a: Iterable[Mapping[str, Any]],
    annotator_b: str,
    entries_b: Iterable[Mapping[str, Any]],
    *,
    generated_at: str | None = None,
) -> AgreementReport:
    """Return the agreement analysis between two annotators. Generates no gold."""
    index_a = _present_index(entries_a)
    index_b = _present_index(entries_b)
    loci = sorted(set(index_a) | set(index_b))

    class_a = [index_a.get(locus, (_NONE, _NONE))[0] or _NONE for locus in loci]
    class_b = [index_b.get(locus, (_NONE, _NONE))[0] or _NONE for locus in loci]

    both = [locus for locus in loci if locus in index_a and locus in index_b]
    disp_a = [index_a[locus][1] or _NONE for locus in both]
    disp_b = [index_b[locus][1] or _NONE for locus in both]

    class_agreement = (
        sum(1 for a, b in zip(class_a, class_b, strict=True) if a == b) / len(loci) if loci else 1.0
    )
    disposition_agreement = (
        sum(1 for a, b in zip(disp_a, disp_b, strict=True) if a == b) / len(both) if both else 1.0
    )

    disagreements: list[dict[str, Any]] = []
    for locus in loci:
        a = index_a.get(locus)
        b = index_b.get(locus)
        if a != b:
            disagreements.append(
                {
                    "dataset_id": locus[0],
                    "support": locus[1],
                    "a": {"class": a[0], "disposition": a[1]} if a else None,
                    "b": {"class": b[0], "disposition": b[1]} if b else None,
                    "kind": "presence" if (a is None or b is None) else "label",
                }
            )

    provenance = provenance_block(
        tool="agreement.analyze",
        inputs=[annotator_a, annotator_b],
        generated_at=generated_at,
    )
    return AgreementReport(
        annotator_a=annotator_a,
        annotator_b=annotator_b,
        n_items=len(loci),
        class_kappa=cohen_kappa(class_a, class_b),
        disposition_kappa=cohen_kappa(disp_a, disp_b),
        class_agreement=class_agreement,
        disposition_agreement=disposition_agreement,
        disagreements=tuple(disagreements),
        provenance=provenance,
    )

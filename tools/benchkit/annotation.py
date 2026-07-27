"""Deliverable 4: annotation package generator.

Prepares annotation packets for human annotators: an artifact-bundle manifest, the
dataset metadata, a blank annotation form per dataset, and a per-annotator
assignment manifest. It never generates a label, never prefills an annotation, and
never infers a class. The class and disposition lists it embeds are the frozen STO
register options an annotator chooses among; the tool makes no choice. The
``annotations`` list on every form is empty by construction.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.tuples import ROWS, TABLE
from synthaudit_bench.sto import load as load_ontology

from benchkit.errors import MissingInputError
from benchkit.provenance import provenance_block

__all__ = ["Packet", "blank_form", "class_options", "generate_packets", "read_header"]


def read_header(path: str | Path) -> tuple[str, ...]:
    """Return the column names from a CSV header (factual; reads nothing else)."""
    source = Path(path)
    if not source.is_file():
        raise MissingInputError(f"data file not found: {source}")
    with source.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle), [])
    return tuple(str(column) for column in header)


def class_options(sto_version: str = "1.0.0") -> list[dict[str, Any]]:
    """Return the STO class reference list (id, name, group, gold_type), for the form.

    This is reference material the annotator selects from; it assigns nothing.
    """
    ontology = load_ontology(sto_version)
    options: list[dict[str, Any]] = []
    for class_def in ontology.classes.values():
        gold_type = getattr(class_def, "gold_type", None)
        options.append(
            {
                "id": class_def.id,
                "name": class_def.name,
                "group": class_def.group,
                "gold_type": getattr(gold_type, "value", gold_type),
            }
        )
    return sorted(options, key=lambda option: option["id"])


def blank_form(
    dataset_id: str,
    *,
    columns: Sequence[str] = (),
    sto_version: str = "1.0.0",
) -> dict[str, Any]:
    """Return a blank annotation form for one dataset. ``annotations`` is empty.

    The form lists the dataset's columns (for support entry), the full STO class and
    disposition option lists (reference only), and the reserved support tokens. It
    contains no labels; the annotator fills ``annotations`` following the manual.
    """
    return {
        "dataset_id": dataset_id,
        "sto_version": sto_version,
        "columns": list(columns),
        "class_options": class_options(sto_version),
        "disposition_options": [d.value for d in Disposition],
        "support_tokens": [ROWS, TABLE],
        "annotation_fields": [
            "support",
            "candidate_class",
            "disposition",
            "present",
            "confidence",
            "evidence",
        ],
        "annotations": [],
    }


@dataclass(frozen=True, slots=True)
class Packet:
    """One annotator's packet: blank forms plus an assignment manifest."""

    annotator_id: str
    forms: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the packet."""
        return {
            "annotator_id": self.annotator_id,
            "manifest": self.manifest,
            "forms": list(self.forms),
        }


def generate_packets(
    assignment: Mapping[str, Sequence[str]],
    *,
    columns: Mapping[str, Sequence[str]] | None = None,
    bundles: Mapping[str, Mapping[str, str]] | None = None,
    sto_version: str = "1.0.0",
    generated_at: str | None = None,
) -> list[Packet]:
    """Return one blank packet per annotator, deterministically ordered.

    ``assignment`` maps annotator id to the dataset ids they will label. ``columns``
    optionally supplies each dataset's columns (for support entry); ``bundles``
    optionally supplies each dataset's file->sha256 artifact-bundle manifest. Every
    form is blank; nothing is inferred or prefilled.
    """
    columns = columns or {}
    bundles = bundles or {}
    packets: list[Packet] = []
    for annotator_id in sorted(assignment):
        dataset_ids = sorted(assignment[annotator_id])
        forms = tuple(
            blank_form(dataset_id, columns=columns.get(dataset_id, ()), sto_version=sto_version)
            for dataset_id in dataset_ids
        )
        manifest = {
            "annotator_id": annotator_id,
            "sto_version": sto_version,
            "datasets": [
                {
                    "dataset_id": dataset_id,
                    "bundle": {
                        name: bundles[dataset_id][name]
                        for name in sorted(bundles.get(dataset_id, {}))
                    },
                }
                for dataset_id in dataset_ids
            ],
            "provenance": provenance_block(
                tool="annotation.packets",
                inputs=[annotator_id, *dataset_ids],
                parameters={"sto_version": sto_version},
                generated_at=generated_at,
            ),
        }
        packets.append(Packet(annotator_id=annotator_id, forms=forms, manifest=manifest))
    return packets

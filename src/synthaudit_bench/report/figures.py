"""Declarative, publication-ready figure specifications over the tidy tables.

Figures are declarative :class:`~synthaudit_bench.model.figures.FigureSpec` values
that name a tidy table and an encoding; they read tidy tables only and carry no
rendering logic, so a figure is reproducible from the specification and the table.
"""

from __future__ import annotations

from synthaudit_bench.model.figures import FigureInput, FigureSpec

__all__ = [
    "class_prevalence_figure",
    "detector_f1_figure",
    "disposition_breakdown_figure",
    "standard_figures",
]


def class_prevalence_figure() -> FigureSpec:
    """A bar figure of STO-class prevalence across the frame."""
    return FigureSpec(
        id="class-prevalence",
        kind="bar",
        caption="Prevalence of STO classes across the corpus.",
        inputs=(FigureInput(table="sto_summary", columns=("sto_class", "count")),),
        encoding={"x": "sto_class", "y": "count"},
    )


def disposition_breakdown_figure() -> FigureSpec:
    """A stacked-bar figure of dispositions across detected relations."""
    return FigureSpec(
        id="disposition-breakdown",
        kind="stacked_bar",
        caption="Disposition breakdown of detected relations.",
        inputs=(FigureInput(table="findings", columns=("disposition", "sto_class")),),
        encoding={"x": "disposition", "color": "sto_class"},
    )


def detector_f1_figure() -> FigureSpec:
    """A bar figure of detection F1 by dataset."""
    return FigureSpec(
        id="detector-f1",
        kind="bar",
        caption="Detection F1 by dataset.",
        inputs=(FigureInput(table="per_dataset_metrics", columns=("dataset_id", "detection_f1")),),
        encoding={"x": "dataset_id", "y": "detection_f1"},
    )


def standard_figures() -> tuple[FigureSpec, ...]:
    """Return the standard figure set, in deterministic id order."""
    return (class_prevalence_figure(), detector_f1_figure(), disposition_breakdown_figure())

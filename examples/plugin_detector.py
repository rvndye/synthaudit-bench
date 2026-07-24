"""Minimal detector-plugin example (mirrors ``docs/detector-protocol.md``).

Run from the repository root with the package installed::

    python examples/plugin_detector.py

It defines a tiny reference-free detector that flags constant columns as STO-S02,
registers it, runs it through the isolated task boundary on an in-memory dataset,
and prints the normalized findings. This is illustrative usage of the public
``Detector`` protocol; it adds no benchmark behavior.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from synthaudit_bench.detector import (
    BaseDetector,
    DetectorCapabilities,
    ExecutionContext,
    RawFinding,
    register_detector,
    run_detector,
)
from synthaudit_bench.model.dataset import DatasetObject


class ConstantColumnDetector(BaseDetector):
    """Flags every single-valued column as STO-S02 (a constant column)."""

    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(
            name="constant-column",
            version="1.0.0",
            required_bench_version="1.0.0",
            sto_categories=frozenset({"S"}),
        )

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Iterable[RawFinding]:
        for column in dataset.columns:
            if dataset.table[column].nunique(dropna=True) <= 1:
                yield RawFinding(identifier="STO-S02", support=(column,), severity="low")


def main() -> None:
    frame = pd.DataFrame(
        {
            "constant": ["x"] * 250,
            "a": [str(i % 5) for i in range(250)],
            "b": [str(i % 7) for i in range(250)],
            "target": [str(i % 2) for i in range(250)],
        }
    )
    dataset = DatasetObject(name="demo", table=frame, target="target")

    registry = register_detector("constant-column", ConstantColumnDetector)
    detector = registry.create("constant-column")
    result = run_detector(detector, dataset, ExecutionContext())

    print(f"detector: {result.detector.name} {result.detector.version}")
    print(f"error:    {result.error}")
    for artifact in result.tuples:
        print(f"finding:  {artifact.sto_class} support={artifact.support}")


if __name__ == "__main__":
    main()

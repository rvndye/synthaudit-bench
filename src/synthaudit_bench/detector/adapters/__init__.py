"""Optional detector adapters.

Adapters wrap concrete auditing systems as :class:`~synthaudit_bench.detector.base.Detector`
implementations. The reference SynthAudit adapter (a separate optional extra) is the
only component that imports the reference implementation; the baseline detector here
depends only on pandas and detects objective structural classes, so the pipeline is
runnable end-to-end without any external tool. The benchmark core remains
detector-agnostic: nothing outside this package imports a specific detector.
"""

from __future__ import annotations

from synthaudit_bench.detector.adapters.baselines import (
    StructuralBaselineDetector,
    builtin_registry,
)

__all__ = ["StructuralBaselineDetector", "builtin_registry"]

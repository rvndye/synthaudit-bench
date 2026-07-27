"""benchkit: benchmark execution infrastructure for SynthAudit-Bench.

This package is **benchmark construction tooling**, not benchmark software and not
benchmark data. It drives the frozen ``synthaudit_bench`` public API to help humans
build the benchmark exactly as the published construction package specifies. It
never fabricates datasets, annotations, gold, expected outputs, or metrics: every
tool consumes real, human-provided inputs and fails closed when they are absent.

Separation of concerns (do not blur these):

* **software**   -> ``src/synthaudit_bench`` (frozen; imported, never modified here).
* **infrastructure** -> this package (``tools/benchkit``).
* **data**       -> ``corpus/``, ``registry/``, ``conformance/`` (produced by humans
  running this tooling; empty until later phases intentionally begin).
"""

from __future__ import annotations

from benchkit.version import __version__

__all__ = ["__version__"]

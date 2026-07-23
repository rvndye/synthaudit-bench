"""SynthAudit-Bench: a reference-free structural trustworthiness benchmark.

This package implements the SynthAudit-Bench specification. The core library is
detector-agnostic and never imports the SynthAudit reference implementation; a
conforming detector is supplied through the ``synthaudit_bench.detector`` plugin
interface. See the frozen specification and the ``docs/`` tree.
"""

from __future__ import annotations

from synthaudit_bench.version import __version__

__all__ = ["__version__"]

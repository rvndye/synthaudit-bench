"""The ``bench`` command-line interface (architecture Section 10).

A thin composition layer over the library. The console entry point is
:func:`synthaudit_bench.cli.main.main`.
"""

from __future__ import annotations

from synthaudit_bench.cli.main import main

__all__ = ["main"]

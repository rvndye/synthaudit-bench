"""Reproducibility invariant: the reported version is stable and static.

The package version must be a fixed literal, not computed at import time, so that
two imports (or two runs) always agree. This guards the determinism contract at
its smallest surface and seeds the reproducibility test tier.
"""

from __future__ import annotations

import importlib

import synthaudit_bench


def test_version_is_stable_across_reimport() -> None:
    """Re-importing the package yields an identical version string."""
    first = synthaudit_bench.__version__
    reloaded = importlib.reload(synthaudit_bench)
    assert reloaded.__version__ == first


def test_version_matches_module_source() -> None:
    """The exported version equals the single source of truth in ``version``."""
    from synthaudit_bench import version

    assert synthaudit_bench.__version__ == version.__version__

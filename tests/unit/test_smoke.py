"""Smoke tests: the package imports cleanly and reports a valid version.

These guard the WP0 scaffold: if packaging or the version source regresses, CI
fails here before any later work package is affected.
"""

from __future__ import annotations

import synthaudit_bench


def test_package_exposes_version() -> None:
    """The package exports a non-empty version string."""
    assert isinstance(synthaudit_bench.__version__, str)
    assert synthaudit_bench.__version__


def test_version_is_semver_triple() -> None:
    """The version begins with a numeric MAJOR.MINOR.PATCH triple."""
    parts = synthaudit_bench.__version__.split(".")
    assert len(parts) >= 3
    assert all(part.isdigit() for part in parts[:3])

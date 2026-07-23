"""Single source of truth for the package version.

This value tracks the *software* that implements the benchmark. It is distinct
from the *benchmark version* (the corpus, ontology, and specification version,
``1.0.0``), which is pinned in ``configs/default.yaml`` and recorded in release
manifests. See ``docs/identity.md`` for the two-version policy.
"""

from __future__ import annotations

__version__ = "0.0.1"

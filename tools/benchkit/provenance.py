"""Provenance stamping for benchkit outputs.

Every artifact benchkit emits carries a provenance block recording the tool, its
version, the frozen software version it ran against, and the inputs it consumed.
Following the frozen software's discipline, no wall-clock is read here: a caller
that wants a timestamp injects it explicitly, so outputs stay reproducible.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from synthaudit_bench.release import version_report

from benchkit.version import __version__

__all__ = ["provenance_block"]


def provenance_block(
    *,
    tool: str,
    inputs: Sequence[str] = (),
    parameters: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic provenance block for a benchkit output.

    ``tool`` names the pipeline step; ``inputs`` are the input identifiers or paths
    consumed; ``parameters`` records the run parameters. ``generated_at`` is an
    optional injected timestamp (omitted from the block when not supplied, so the
    block is reproducible by default).
    """
    block: dict[str, Any] = {
        "tool": tool,
        "benchkit_version": __version__,
        "software": version_report(),
        "inputs": sorted(inputs),
    }
    if parameters:
        block["parameters"] = {key: parameters[key] for key in sorted(parameters)}
    if generated_at is not None:
        block["generated_at"] = generated_at
    return block

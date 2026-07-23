"""Shared pytest configuration for the SynthAudit-Bench test suite."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

import pytest


@pytest.fixture
def sto_register() -> dict[str, Any]:
    """The decoded canonical STO v1.0 register, for consistency-check fixtures.

    Tests mutate deep copies of this mapping to exercise the loader's structural
    validation without altering the packaged register.
    """
    text = (resources.files("synthaudit_bench.sto_data") / "STO-1.0.0.json").read_text(
        encoding="utf-8"
    )
    result: dict[str, Any] = json.loads(text)
    return result

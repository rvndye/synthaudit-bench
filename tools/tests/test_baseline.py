"""Tests for the baseline runner.

The runner drives the frozen ``bench`` CLI. The end-to-end test runs over a synthetic
fixture CSV in a temp directory (an isolated unit-test fixture, not benchmark data)
and produces no benchmark artifact or reported result.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from benchkit.baseline import report_template, run_baseline
from benchkit.errors import MissingInputError


def _fixture_csv(path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["k", "b", "c", "g"])
        writer.writeheader()
        for i in range(250):
            writer.writerow({"k": "1", "b": str(i % 4), "c": str(i % 4), "g": str(i % 2)})
    return path


def test_no_inputs_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(MissingInputError):
        run_baseline([tmp_path / "does-not-exist.csv"], tmp_path / "out")


def test_report_template_blank_without_metrics() -> None:
    row = report_template("public-dev", "structural-baseline", None)
    assert row["detector"] == "structural-baseline"
    assert row["detection_micro_f1"] is None
    assert row["objective_recall"] is None


def test_runs_frozen_cli_over_fixture(tmp_path: Path) -> None:
    csv_path = _fixture_csv(tmp_path / "fx.csv")
    run = run_baseline([csv_path], tmp_path / "out", split="public-dev", target="g")
    assert run.ran
    assert run.steps["audit"] == 0
    assert run.schema_valid["run-manifest"] is True
    # No gold supplied: no metrics fabricated; the template stays blank.
    assert run.metrics is None
    assert run.template["detection_micro_f1"] is None

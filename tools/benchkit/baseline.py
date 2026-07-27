"""Deliverable 9: baseline runner.

Orchestration that executes the *frozen* ``bench`` CLI over a completed benchmark
release: it invokes the existing CLI (never reimplements it), collects the outputs,
validates them against the frozen schemas, aggregates the real metrics, and fills a
report template. No benchmark execution happens unless benchmark inputs exist: with
no dataset files, the runner fails closed and invokes nothing. It fabricates no
metric; every value in the report template comes from a real CLI run or is left
blank.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.schemas.errors import SchemaValidationError

from benchkit.errors import BenchkitError, MissingInputError, ValidationError
from benchkit.jsonlio import read_json
from benchkit.provenance import provenance_block

__all__ = ["BaselineRun", "report_template", "run_baseline", "run_cli"]

_CLI = [sys.executable, "-m", "synthaudit_bench.cli.main"]
_RESULT_COLUMNS = (
    "detector",
    "split",
    "detection_micro_f1",
    "detection_macro_class_f1",
    "detection_macro_dataset_f1",
    "disposition_micro_f1",
    "objective_recall",
    "adjudicated_recall",
    "detection_micro_precision",
    "coverage",
)


def run_cli(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Invoke the frozen ``bench`` CLI (``python -m synthaudit_bench.cli.main``)."""
    return subprocess.run([*_CLI, *args], capture_output=True, text=True, check=False)


@dataclass(slots=True)
class BaselineRun:
    """The outcome of a baseline run over a release."""

    ran: bool
    detector: str
    split: str
    steps: dict[str, int] = field(default_factory=dict)
    schema_valid: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, Any] | None = None
    template: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    note: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the run."""
        mapping: dict[str, Any] = {
            "ran": self.ran,
            "detector": self.detector,
            "split": self.split,
            "steps": {key: self.steps[key] for key in sorted(self.steps)},
            "schema_valid": {key: self.schema_valid[key] for key in sorted(self.schema_valid)},
            "template": self.template,
            "provenance": self.provenance,
        }
        if self.metrics is not None:
            mapping["metrics"] = self.metrics
        if self.note is not None:
            mapping["note"] = self.note
        return mapping


def report_template(split: str, detector: str, metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Return the results-table row, filled from real metrics or left blank.

    The columns follow the Evaluation Protocol. Values are populated only from an
    actual metrics table; when metrics are absent every metric column is null.
    """
    row: dict[str, Any] = dict.fromkeys(_RESULT_COLUMNS)
    row["detector"] = detector
    row["split"] = split
    if metrics is not None:
        detection = metrics.get("detection", {})
        disposition = metrics.get("disposition_aware", {})
        coverage = metrics.get("coverage", {})
        micro = detection.get("micro", {})
        row["detection_micro_f1"] = micro.get("f1")
        row["detection_micro_precision"] = micro.get("precision")
        row["detection_macro_class_f1"] = detection.get("macro_class_f1")
        row["detection_macro_dataset_f1"] = detection.get("macro_dataset_f1")
        row["disposition_micro_f1"] = disposition.get("micro", {}).get("f1")
        row["objective_recall"] = coverage.get("objective_gold_recall")
        row["adjudicated_recall"] = coverage.get("adjudicated_gold_recall")
        row["coverage"] = coverage
    return row


def _validate(name: str, instance: Any) -> bool:
    try:
        schemas.validate_instance(name, instance)
    except SchemaValidationError:
        return False
    return True


def run_baseline(
    csvs: Sequence[str | Path],
    out_dir: str | Path,
    *,
    gold_dir: str | Path | None = None,
    split: str = "public-dev",
    target: str | None = None,
    jobs: int = 1,
    seed: int = 42,
    detector: str = "structural-baseline",
    generated_at: str | None = None,
) -> BaselineRun:
    """Run the frozen baseline pipeline over ``csvs`` and collect validated outputs.

    Fails closed if no dataset inputs exist (the benchmark is empty). Runs
    ``bench audit`` (and ``bench match`` when gold is supplied and ``bench report``),
    validates the manifest and metrics against the frozen schemas, and fills the
    report template from the real metrics. Invokes the existing CLI only.
    """
    inputs = [Path(c) for c in csvs]
    provenance = provenance_block(
        tool="baseline.run",
        inputs=[str(p) for p in inputs],
        parameters={"split": split, "seed": seed, "jobs": jobs, "detector": detector},
        generated_at=generated_at,
    )
    present = [p for p in inputs if p.is_file()]
    if not present:
        # No benchmark inputs exist: do not invoke the CLI (fail closed).
        raise MissingInputError(
            "no benchmark inputs exist; the baseline runner will not execute on an empty corpus"
        )

    out = Path(out_dir)
    run = BaselineRun(ran=True, detector=detector, split=split, provenance=provenance)

    audit_args = [
        "audit",
        *[str(p) for p in present],
        "--split",
        split,
        "--out",
        str(out),
        "--jobs",
        str(jobs),
        "--seed",
        str(seed),
    ]
    if target is not None:
        audit_args += ["--target", target]
    audit = run_cli(audit_args)
    run.steps["audit"] = audit.returncode
    if audit.returncode not in (0, 5):  # 0 ok, 5 partial dataset failures
        raise BenchkitError(f"bench audit failed (exit {audit.returncode}): {audit.stderr.strip()}")

    manifest_path = out / "manifest.json"
    run.schema_valid["run-manifest"] = _validate("run-manifest", read_json(manifest_path))

    if gold_dir is not None and Path(gold_dir).is_dir():
        match = run_cli(
            ["match", "--audits", str(out / "audits"), "--gold", str(gold_dir), "--split", split]
        )
        run.steps["match"] = match.returncode
        if match.returncode == 0:
            metrics = read_json_from_text(match.stdout)
            run.schema_valid["metrics"] = _validate("metrics", metrics)
            if not run.schema_valid["metrics"]:
                raise ValidationError("bench match produced a metrics table that failed schema")
            run.metrics = metrics
        else:
            run.note = f"match did not score (exit {match.returncode})"

    report = run_cli(["report", "--audits", str(out / "audits"), "--format", "json"])
    run.steps["report"] = report.returncode

    run.template = report_template(split, detector, run.metrics)
    return run


def read_json_from_text(text: str) -> Any:
    """Parse JSON from CLI stdout, failing closed on malformed output."""
    import json

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"CLI produced non-JSON output: {exc}") from exc

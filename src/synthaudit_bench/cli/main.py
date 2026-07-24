"""The ``bench`` command-line interface (architecture Section 10).

A thin CLI over the library: each subcommand parses arguments and calls one library
function, returning the Section 10 exit codes (0 success; 2 input/validation; 3
integrity; 5 partial dataset failures; 6 policy/compliance block). It makes the
benchmark runnable end-to-end: load CSV datasets, audit them with the built-in
structural baseline, score against gold, aggregate into reports, run the compliance
suite, and report versions and the release manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from synthaudit_bench.compliance import run_compliance
from synthaudit_bench.detector.adapters.baselines import StructuralBaselineDetector
from synthaudit_bench.gold.errors import GoldError
from synthaudit_bench.gold.loader import load_gold_dir
from synthaudit_bench.gold.scoring import evaluate
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.results import AuditResult
from synthaudit_bench.registry.errors import RegistryError
from synthaudit_bench.registry.loader import load_registry
from synthaudit_bench.release import build_release_manifest, dataset_manifest_entry, version_report
from synthaudit_bench.report.render import build_report, render_json_report, render_markdown_report
from synthaudit_bench.runner.engine import run_benchmark, write_artifacts

_OK = 0
_INPUT = 2
_PARTIAL = 5
_COMPLIANCE = 6


def _load_csv(path: Path, target: str | None) -> DatasetObject:
    table = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    table.columns = [str(column) for column in table.columns]
    resolved_target = target if target is not None and target in table.columns else None
    return DatasetObject(name=path.stem, table=table, target=resolved_target)


def _load_audits(audits_dir: Path) -> list[AuditResult]:
    results: list[AuditResult] = []
    for path in sorted(audits_dir.glob("*.json")):
        results.append(AuditResult.from_mapping(json.loads(path.read_text(encoding="utf-8"))))
    return results


def _cmd_version(_: argparse.Namespace) -> int:
    print(json.dumps(version_report(), indent=2, sort_keys=True))
    return _OK


def _cmd_registry(args: argparse.Namespace) -> int:
    try:
        registry = load_registry(args.root)
    except RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return _INPUT
    for entry in registry.datasets():
        print(f"{entry.corpus.value}\t{entry.id}")
    return _OK


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return _INPUT
    print(f"registry valid: {len(registry)} records")
    return _OK


def _cmd_audit(args: argparse.Namespace) -> int:
    datasets = [_load_csv(Path(path), args.target) for path in args.csv]
    outcome = run_benchmark(
        datasets,
        StructuralBaselineDetector(),
        split=args.split,
        root_seed=args.seed,
        jobs=args.jobs,
    )
    if args.out:
        write_artifacts(outcome, args.out)
    print(
        json.dumps({"run_id": outcome.run_id, "scored": outcome.scored, "failed": outcome.failed})
    )
    return _PARTIAL if outcome.failed else _OK


def _cmd_match(args: argparse.Namespace) -> int:
    results = _load_audits(Path(args.audits))
    try:
        gold = load_gold_dir(args.gold)
        table = evaluate(results, gold, split=args.split)
    except GoldError as exc:
        print(f"match error: {exc}", file=sys.stderr)
        return _INPUT
    print(json.dumps(table.to_mapping(), indent=2, sort_keys=True))
    return _OK


def _cmd_report(args: argparse.Namespace) -> int:
    results = _load_audits(Path(args.audits))
    report = build_report(results, split=args.split)
    if args.format == "md":
        print(render_markdown_report(report))
    else:
        print(render_json_report(report))
    return _OK


def _cmd_compliance(args: argparse.Namespace) -> int:
    datasets = [_load_csv(Path(path), args.target) for path in args.csv]
    try:
        gold = load_gold_dir(args.gold)
    except GoldError as exc:
        print(f"compliance error: {exc}", file=sys.stderr)
        return _INPUT
    record = run_compliance(StructuralBaselineDetector(), datasets, gold)
    print(
        json.dumps(
            {**record.to_mapping(), "result_hash": record.result_hash()}, indent=2, sort_keys=True
        )
    )
    return _OK if record.passed else _COMPLIANCE


def _cmd_release(args: argparse.Namespace) -> int:
    datasets = [_load_csv(Path(path), None) for path in args.csv]
    entries = [
        dataset_manifest_entry(dataset, corpus=args.corpus, license=args.license, source=())
        for dataset in datasets
    ]
    manifest = build_release_manifest(entries)
    manifest["version_report"] = version_report()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return _OK


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bench", description="SynthAudit-Bench command line.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="print software, benchmark, and schema versions").set_defaults(
        func=_cmd_version
    )

    registry = sub.add_parser("registry", help="list registry datasets")
    registry.add_argument("root")
    registry.set_defaults(func=_cmd_registry)

    validate = sub.add_parser("validate", help="validate a registry")
    validate.add_argument("--registry", required=True)
    validate.set_defaults(func=_cmd_validate)

    audit = sub.add_parser("audit", help="audit CSV datasets with the structural baseline")
    audit.add_argument("csv", nargs="+")
    audit.add_argument("--target", default=None)
    audit.add_argument("--split", default="public-dev")
    audit.add_argument("--out", default=None)
    audit.add_argument("--jobs", type=int, default=1)
    audit.add_argument("--seed", type=int, default=42)
    audit.set_defaults(func=_cmd_audit)

    match = sub.add_parser("match", help="score audit results against gold")
    match.add_argument("--audits", required=True)
    match.add_argument("--gold", required=True)
    match.add_argument("--split", default="public-dev")
    match.set_defaults(func=_cmd_match)

    report = sub.add_parser("report", help="aggregate audit results into a report")
    report.add_argument("--audits", required=True)
    report.add_argument("--split", default="public-dev")
    report.add_argument("--format", choices=("json", "md"), default="json")
    report.set_defaults(func=_cmd_report)

    compliance = sub.add_parser("compliance", help="run the compliance suite against the baseline")
    compliance.add_argument("csv", nargs="+")
    compliance.add_argument("--gold", required=True)
    compliance.add_argument("--target", default=None)
    compliance.set_defaults(func=_cmd_compliance)

    release = sub.add_parser("release", help="build the release manifest and version report")
    release.add_argument("csv", nargs="*")
    release.add_argument("--corpus", default="evaluation")
    release.add_argument("--license", default="unknown")
    release.set_defaults(func=_cmd_release)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` and dispatch to the selected command, returning its exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


def run() -> None:  # pragma: no cover - console entry point
    """Console entry point: run :func:`main` and exit with its code."""
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    run()

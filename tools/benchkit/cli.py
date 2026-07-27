"""The ``benchkit`` command-line interface.

A thin, deterministic composition layer over the benchkit pipelines. It is separate
from the frozen ``bench`` CLI: ``bench`` runs the benchmark, ``benchkit`` builds it.
Every command reads human-provided inputs and fails closed (exit 1) on any benchkit
error; it fabricates nothing. With no inputs, commands have nothing to do.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from benchkit import __version__
from benchkit.acquisition import acquire_records, records_from_registry
from benchkit.agreement import analyze_agreement
from benchkit.annotation import generate_packets
from benchkit.baseline import run_baseline
from benchkit.census import CandidateInput, enumerate_candidates
from benchkit.corpus import DesignSpec, plan_corpus, pool_from_census
from benchkit.errors import BenchkitError
from benchkit.goldassembly import assemble_gold, gold_files
from benchkit.jsonlio import read_json, read_jsonl, write_json, write_jsonl
from benchkit.packaging import validate_release
from benchkit.validation import validate_annotations

_OK = 0
_FAIL = 1


def _candidate(row: dict[str, Any]) -> CandidateInput:
    file = row.get("file")
    return CandidateInput(
        source_key=str(row["source_key"]),
        title=str(row.get("title", "")),
        source_urls=tuple(str(u) for u in row.get("source_urls", [])),
        retrieved=str(row.get("retrieved", "")),
        file=Path(str(file)) if file else None,
        declared_license=row.get("declared_license"),
        declared_generator_family=row.get("declared_generator_family"),
        declared_domain=row.get("declared_domain"),
        notes=row.get("notes"),
    )


def _cmd_census(args: argparse.Namespace) -> int:
    candidates = [_candidate(row) for row in read_jsonl(args.candidates)]
    records = enumerate_candidates(candidates, prefix=args.prefix)
    n = write_jsonl(args.out, (r.to_mapping() for r in records))
    print(f"census: {n} record(s) -> {args.out}")
    return _OK


def _cmd_acquire(args: argparse.Namespace) -> int:
    records = records_from_registry(args.registry)
    report = acquire_records(records, args.cache, require_data=args.require_data)
    write_json(args.out, report.to_mapping())
    print(
        f"acquire: {report.to_mapping()['n_verified']} verified, "
        f"{report.to_mapping()['n_stub']} stub, {len(report.failures)} failed -> {args.out}"
    )
    return _OK if report.ok else _FAIL


def _cmd_corpus(args: argparse.Namespace) -> int:
    pool = pool_from_census(read_jsonl(args.census))
    spec = DesignSpec(
        root_seed=args.seed,
        held_out_fraction=args.held_out_fraction,
        balance_key=args.balance_key,
        select_limit=args.limit,
    )
    plan = plan_corpus(pool, spec)
    write_json(args.out, plan.to_mapping())
    print(f"corpus: {len(plan.items)} selected, leakage_ok={plan.leakage_ok} -> {args.out}")
    return _OK


def _cmd_annotation_package(args: argparse.Namespace) -> int:
    assignment = read_json(args.assignment)
    columns = read_json(args.columns) if args.columns else None
    packets = generate_packets(assignment, columns=columns, sto_version=args.sto_version)
    out = Path(args.out)
    for packet in packets:
        write_json(out / f"{packet.annotator_id}.packet.json", packet.to_mapping())
    print(f"annotation: {len(packets)} packet(s) -> {out}")
    return _OK


def _cmd_annotation_validate(args: argparse.Namespace) -> int:
    entries = list(read_jsonl(args.annotations))
    report = validate_annotations(entries, sto_version=args.sto_version)
    if args.out:
        write_json(args.out, report.to_mapping())
    print(f"validate: {report.n_entries} entries, {len(report.issues)} issue(s), ok={report.ok}")
    return _OK if report.ok else _FAIL


def _cmd_agreement(args: argparse.Namespace) -> int:
    report = analyze_agreement(
        args.annotator_a,
        list(read_jsonl(args.a)),
        args.annotator_b,
        list(read_jsonl(args.b)),
    )
    if args.out:
        write_json(args.out, report.to_mapping())
    print(
        f"agreement: class_kappa={report.class_kappa:.4f} "
        f"disposition_kappa={report.disposition_kappa:.4f} n={report.n_items}"
    )
    return _OK


def _cmd_gold(args: argparse.Namespace) -> int:
    assembly = assemble_gold(list(read_jsonl(args.annotations)), sto_version=args.sto_version)
    out = Path(args.out)
    for did, tuples in gold_files(assembly).items():
        write_json(out / f"{did}.json", tuples)
    print(
        f"gold: {assembly.n_tuples} tuple(s) across {len(assembly.by_dataset)} dataset(s) -> {out}"
    )
    return _OK


def _cmd_package(args: argparse.Namespace) -> int:
    result = validate_release(
        args.registry, gold_dir=args.gold, splits_path=args.splits, sto_version=args.sto_version
    )
    if args.out:
        write_json(args.out, result.to_mapping())
    print(f"package: ok={result.ok} rules={result.to_mapping()['rules']}")
    return _OK if result.ok else _FAIL


def _cmd_baseline(args: argparse.Namespace) -> int:
    run = run_baseline(
        args.csv,
        args.out_dir,
        gold_dir=args.gold,
        split=args.split,
        target=args.target,
        jobs=args.jobs,
        seed=args.seed,
    )
    if args.report:
        write_json(args.report, run.to_mapping())
    print(f"baseline: ran={run.ran} steps={run.steps} metrics={'yes' if run.metrics else 'no'}")
    return _OK


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchkit", description="SynthAudit-Bench construction tooling."
    )
    parser.add_argument("--version", action="version", version=f"benchkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    census = sub.add_parser("census", help="enumerate census candidates into JSONL records")
    census_sub = census.add_subparsers(dest="census_cmd", required=True)
    enum = census_sub.add_parser("enumerate", help="enumerate candidates (no annotation)")
    enum.add_argument("--candidates", required=True)
    enum.add_argument("--out", required=True)
    enum.add_argument("--prefix", default="census")
    enum.set_defaults(func=_cmd_census)

    acq = sub.add_parser("acquire", help="acquire records via the frozen acquisition (fail closed)")
    acq.add_argument("--registry", required=True)
    acq.add_argument("--cache", required=True)
    acq.add_argument("--out", required=True)
    acq.add_argument("--require-data", action="store_true")
    acq.set_defaults(func=_cmd_acquire)

    corpus = sub.add_parser("corpus", help="plan an evaluation corpus over a census pool")
    corpus_sub = corpus.add_subparsers(dest="corpus_cmd", required=True)
    plan = corpus_sub.add_parser("plan", help="deterministic sampling, balancing, held-out")
    plan.add_argument("--census", required=True)
    plan.add_argument("--out", required=True)
    plan.add_argument("--seed", type=int, default=42)
    plan.add_argument("--held-out-fraction", type=float, default=0.0)
    plan.add_argument("--balance-key", default=None)
    plan.add_argument("--limit", type=int, default=None)
    plan.set_defaults(func=_cmd_corpus)

    ann = sub.add_parser("annotation", help="annotation packet generation and validation")
    ann_sub = ann.add_subparsers(dest="ann_cmd", required=True)
    pkg = ann_sub.add_parser("package", help="generate blank annotation packets")
    pkg.add_argument("--assignment", required=True)
    pkg.add_argument("--columns", default=None)
    pkg.add_argument("--out", required=True)
    pkg.add_argument("--sto-version", default="1.0.0")
    pkg.set_defaults(func=_cmd_annotation_package)
    val = ann_sub.add_parser("validate", help="validate completed annotations (fail closed)")
    val.add_argument("--annotations", required=True)
    val.add_argument("--out", default=None)
    val.add_argument("--sto-version", default="1.0.0")
    val.set_defaults(func=_cmd_annotation_validate)

    agr = sub.add_parser("agreement", help="inter-annotator agreement (no gold)")
    agr.add_argument("--a", required=True)
    agr.add_argument("--b", required=True)
    agr.add_argument("--annotator-a", required=True)
    agr.add_argument("--annotator-b", required=True)
    agr.add_argument("--out", default=None)
    agr.set_defaults(func=_cmd_agreement)

    gold = sub.add_parser("gold", help="assemble gold from reconciled annotations")
    gold_sub = gold.add_subparsers(dest="gold_cmd", required=True)
    assemble = gold_sub.add_parser("assemble", help="convert reconciled annotations to gold files")
    assemble.add_argument("--annotations", required=True)
    assemble.add_argument("--out", required=True)
    assemble.add_argument("--sto-version", default="1.0.0")
    assemble.set_defaults(func=_cmd_gold)

    package = sub.add_parser("package", help="validate a benchmark release structure")
    package_sub = package.add_subparsers(dest="package_cmd", required=True)
    pv = package_sub.add_parser("validate", help="structural release validation (Section 6.1.6)")
    pv.add_argument("--registry", required=True)
    pv.add_argument("--gold", default=None)
    pv.add_argument("--splits", default=None)
    pv.add_argument("--out", default=None)
    pv.add_argument("--sto-version", default="1.0.0")
    pv.set_defaults(func=_cmd_package)

    baseline = sub.add_parser("baseline", help="run the frozen CLI over a completed release")
    baseline_sub = baseline.add_subparsers(dest="baseline_cmd", required=True)
    run = baseline_sub.add_parser("run", help="audit -> match -> report via the frozen bench CLI")
    run.add_argument("--csv", nargs="+", required=True)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--gold", default=None)
    run.add_argument("--split", default="public-dev")
    run.add_argument("--target", default=None)
    run.add_argument("--jobs", type=int, default=1)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--report", default=None)
    run.set_defaults(func=_cmd_baseline)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv``, dispatch, and fail closed (exit 1) on any benchkit error."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
    except BenchkitError as exc:
        print(f"benchkit error: {exc}", file=sys.stderr)
        return _FAIL
    return result


def run() -> None:  # pragma: no cover - console entry point
    """Console entry point."""
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    run()

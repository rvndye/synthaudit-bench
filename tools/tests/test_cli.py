"""End-to-end tests for the benchkit CLI."""

from __future__ import annotations

import json
from pathlib import Path

from benchkit.cli import main

from _fixtures import annotation_entry


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_version() -> None:
    # argparse --version exits 0 via SystemExit.
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0


def test_census_enumerate(tmp_path: Path) -> None:
    candidates = _write_jsonl(
        tmp_path / "cand.jsonl",
        [{"source_key": "k1", "title": "T", "source_urls": ["u"], "retrieved": "2026-01-01"}],
    )
    out = tmp_path / "census.jsonl"
    assert main(["census", "enumerate", "--candidates", str(candidates), "--out", str(out)]) == 0
    assert out.is_file()
    assert len(out.read_text().strip().splitlines()) == 1


def test_corpus_plan(tmp_path: Path) -> None:
    census = _write_jsonl(
        tmp_path / "census.jsonl",
        [{"id": f"item-{i}", "declared": {"generator_family": "gan"}} for i in range(6)],
    )
    out = tmp_path / "plan.json"
    code = main(
        ["corpus", "plan", "--census", str(census), "--out", str(out), "--held-out-fraction", "0.5"]
    )
    assert code == 0
    plan = json.loads(out.read_text())
    assert plan["leakage_ok"] is True


def test_annotation_validate_ok_and_fail(tmp_path: Path) -> None:
    good = _write_jsonl(tmp_path / "good.jsonl", [annotation_entry()])
    assert main(["annotation", "validate", "--annotations", str(good)]) == 0

    bad = _write_jsonl(tmp_path / "bad.jsonl", [annotation_entry(disposition="bogus")])
    assert main(["annotation", "validate", "--annotations", str(bad)]) == 1


def test_missing_input_fails_closed(tmp_path: Path) -> None:
    assert main(["annotation", "validate", "--annotations", str(tmp_path / "nope.jsonl")]) == 1


def test_gold_assemble(tmp_path: Path) -> None:
    entries = _write_jsonl(
        tmp_path / "reconciled.jsonl",
        [annotation_entry(gold_type="adjudicated")],
    )
    out = tmp_path / "gold"
    assert main(["gold", "assemble", "--annotations", str(entries), "--out", str(out)]) == 0
    assert (out / "fx-1.json").is_file()

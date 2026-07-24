"""End-to-end tests for the ``bench`` command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from synthaudit_bench.cli.main import main
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ROWS, GoldTuple

pytestmark = pytest.mark.integration


def _structured_csv(path: Path) -> Path:
    pd.DataFrame(
        {
            "k": ["1"] * 250,
            "b": [str(i % 4) for i in range(250)],
            "c": [str(i % 4) for i in range(250)],
            "g": [str(i % 2) for i in range(250)],
        }
    ).to_csv(path, index=False)
    return path


def _gold_dir(directory: Path, dataset_id: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    gold = [
        GoldTuple(
            frozenset({"k"}),
            frozenset({"STO-S02"}),
            frozenset({Disposition.NOT_APPLICABLE}),
            GoldType.OBJECTIVE,
            evidence="e",
        ),
        GoldTuple(
            frozenset({"b", "c"}),
            frozenset({"STO-A08"}),
            frozenset({Disposition.REDUNDANCY}),
            GoldType.OBJECTIVE,
            evidence="e",
        ),
        GoldTuple(
            ROWS,
            frozenset({"STO-S01"}),
            frozenset({Disposition.NOT_APPLICABLE}),
            GoldType.OBJECTIVE,
            evidence="e",
        ),
    ]
    (directory / f"{dataset_id}.json").write_text(
        json.dumps([g.to_mapping() for g in gold]), encoding="utf-8"
    )
    return directory


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert json.loads(capsys.readouterr().out)["benchmark"] == "1.0.0"


def test_registry_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registry", "registry"]) == 0  # the repo's illustrative registry
    assert capsys.readouterr().out.strip() != ""


def test_registry_invalid(tmp_path: Path) -> None:
    (tmp_path / "census").mkdir()
    (tmp_path / "census" / "bad.yaml").write_text("just a string", encoding="utf-8")
    assert main(["registry", str(tmp_path)]) == 2


def test_validate_command_ok_and_bad(tmp_path: Path) -> None:
    assert main(["validate", "--registry", "registry"]) == 0
    (tmp_path / "census").mkdir()
    (tmp_path / "census" / "bad.yaml").write_text("- 1\n- 2", encoding="utf-8")
    assert main(["validate", "--registry", str(tmp_path)]) == 2


def test_audit_match_report_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    out = tmp_path / "out"
    assert (
        main(["audit", str(csv), "--target", "g", "--split", "public-dev", "--out", str(out)]) == 0
    )
    capsys.readouterr()
    audits = out / "audits"
    assert (audits / "d1.json").is_file()

    gold = _gold_dir(tmp_path / "gold", "d1")
    assert (
        main(["match", "--audits", str(audits), "--gold", str(gold), "--split", "public-dev"]) == 0
    )
    metrics = json.loads(capsys.readouterr().out)
    assert metrics["detection"]["micro"]["tp"] >= 1

    assert main(["report", "--audits", str(audits), "--format", "md"]) == 0
    assert "SynthAudit-Bench report" in capsys.readouterr().out
    assert main(["report", "--audits", str(audits), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["split"] == "public-dev"


def test_audit_without_out(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    assert main(["audit", str(csv), "--target", "g"]) == 0
    assert "run_id" in capsys.readouterr().out


def test_compliance_gold_error(tmp_path: Path) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    bad = tmp_path / "g"
    bad.mkdir()
    (bad / "d1.json").write_text(
        json.dumps([{"support": ["a"], "classes": ["STO-A01"], "gold_type": "bad"}]),
        encoding="utf-8",
    )
    assert main(["compliance", str(csv), "--gold", str(bad)]) == 2


def test_match_gold_error(tmp_path: Path) -> None:
    (tmp_path / "audits").mkdir()
    bad_gold = tmp_path / "gold"
    bad_gold.mkdir()
    (bad_gold / "d1.json").write_text(
        json.dumps([{"support": ["a"], "classes": ["STO-A01"], "gold_type": "bad"}]),
        encoding="utf-8",
    )
    # an empty audits dir plus schema-invalid gold -> input error
    assert main(["match", "--audits", str(tmp_path / "audits"), "--gold", str(bad_gold)]) == 2


def test_compliance_pass_and_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    gold = _gold_dir(tmp_path / "gold", "d1")
    assert main(["compliance", str(csv), "--gold", str(gold), "--target", "g"]) == 0
    capsys.readouterr()

    clean = tmp_path / "clean.csv"
    pd.DataFrame(
        {
            "a": [str(i) for i in range(250)],
            "b": [str(i + 1000) for i in range(250)],
            "c": [str(i + 2000) for i in range(250)],
            "d": [str(i + 3000) for i in range(250)],
        }
    ).to_csv(clean, index=False)
    clean_gold = tmp_path / "cgold"
    clean_gold.mkdir()
    miss = GoldTuple(
        frozenset({"a"}),
        frozenset({"STO-S02"}),
        frozenset({Disposition.NOT_APPLICABLE}),
        GoldType.OBJECTIVE,
        evidence="e",
    )
    (clean_gold / "clean.json").write_text(json.dumps([miss.to_mapping()]), encoding="utf-8")
    assert main(["compliance", str(clean), "--gold", str(clean_gold)]) == 6


def test_release_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    assert main(["release", str(csv), "--corpus", "evaluation", "--license", "CC0"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["datasets"][0]["id"] == "d1"
    assert manifest["version_report"]["benchmark"] == "1.0.0"

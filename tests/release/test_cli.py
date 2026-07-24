"""End-to-end tests for the ``bench`` command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from synthaudit_bench.acquire import ChecksumError
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


def test_match_gold_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    out = tmp_path / "out"
    assert main(["audit", str(csv), "--target", "g", "--out", str(out)]) == 0
    capsys.readouterr()
    bad_gold = tmp_path / "gold"
    bad_gold.mkdir()
    (bad_gold / "d1.json").write_text(
        json.dumps([{"support": ["a"], "classes": ["STO-A01"], "gold_type": "bad"}]),
        encoding="utf-8",
    )
    # a populated audits dir plus schema-invalid gold -> input error via GoldError
    assert main(["match", "--audits", str(out / "audits"), "--gold", str(bad_gold)]) == 2


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


def test_fetch_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cache = tmp_path / "cache"
    # The repo's illustrative registry declares fetch stubs (no redistributable data),
    # so offline acquisition returns stubs and the command succeeds (exit 0).
    assert main(["fetch", "registry", "--cache", str(cache)]) == 0
    fetched = json.loads(capsys.readouterr().out)["fetched"]
    assert fetched and all("dataset_id" in row for row in fetched)


def test_fetch_registry_error(tmp_path: Path) -> None:
    (tmp_path / "census").mkdir()
    (tmp_path / "census" / "bad.yaml").write_text("just a string", encoding="utf-8")
    assert main(["fetch", str(tmp_path), "--cache", str(tmp_path / "cache")]) == 2


def test_reproduce_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    assert main(["reproduce", str(csv), "--target", "g"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["reproduced"] is True
    assert payload["manifest_match"] is True
    assert payload["results_match"] is True


def test_audit_duplicate_id_is_config_error(tmp_path: Path) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    # The same CSV twice yields two datasets sharing an id: a planning abort that
    # Section 10 maps to exit 2 for ``audit``, surfaced as a clean code not a traceback.
    assert main(["audit", str(csv), str(csv), "--target", "g"]) == 2


def test_match_empty_audits_is_input_error(tmp_path: Path) -> None:
    empty = tmp_path / "audits"
    empty.mkdir()
    gold = _gold_dir(tmp_path / "gold", "d1")
    assert main(["match", "--audits", str(empty), "--gold", str(gold)]) == 2


def test_report_empty_audits_is_input_error(tmp_path: Path) -> None:
    empty = tmp_path / "audits"
    empty.mkdir()
    assert main(["report", "--audits", str(empty)]) == 2


def test_fetch_require_data_acquire_error(tmp_path: Path) -> None:
    # With --require-data and no fetcher, a record whose data is not cached raises a
    # ResourceError (an AcquireError), which fetch maps to exit 4 (external/network).
    assert main(["fetch", "registry", "--cache", str(tmp_path / "cache"), "--require-data"]) == 4


def test_fetch_integrity_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _corrupt(*args: object, **kwargs: object) -> object:
        raise ChecksumError("cached bytes contradict the declared hash")

    # A checksum mismatch during acquisition is an integrity failure: fetch exit 3.
    # ``synthaudit_bench.cli.main`` the submodule is shadowed by the ``main`` function
    # re-exported on the package, so patch the module object via ``sys.modules``.
    monkeypatch.setattr(sys.modules["synthaudit_bench.cli.main"], "acquire_dataset", _corrupt)
    assert main(["fetch", "registry", "--cache", str(tmp_path / "cache")]) == 3


def test_reproduce_duplicate_id_is_config_error(tmp_path: Path) -> None:
    csv = _structured_csv(tmp_path / "d1.csv")
    # A planning abort inside the double run surfaces as the audit-style config code.
    assert main(["reproduce", str(csv), str(csv), "--target", "g"]) == 2

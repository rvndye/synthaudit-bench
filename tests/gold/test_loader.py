"""Unit tests for gold loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from synthaudit_bench.gold import load_gold, load_gold_dir
from synthaudit_bench.gold.errors import InvalidGoldError

_RECORD: dict[str, Any] = {
    "support": ["a", "b"],
    "classes": ["STO-A01"],
    "dispositions": ["structural_constraint"],
    "gold_type": "objective",
    "evidence": "an identity",
}


def test_load_gold_from_list() -> None:
    result = load_gold([_RECORD])
    assert len(result) == 1
    assert result[0].classes == frozenset({"STO-A01"})


@pytest.mark.parametrize("key", ["gold", "tuples", "items"])
def test_load_gold_from_mapping(key: str) -> None:
    assert len(load_gold({key: [_RECORD]})) == 1


def test_load_gold_from_path(tmp_path: Path) -> None:
    path = tmp_path / "d1.json"
    path.write_text(json.dumps([_RECORD]), encoding="utf-8")
    assert len(load_gold(path)) == 1


def test_load_gold_mapping_without_gold_key() -> None:
    with pytest.raises(InvalidGoldError, match="must carry a 'gold' list"):
        load_gold({"other": []})


def test_load_gold_field_not_list() -> None:
    with pytest.raises(InvalidGoldError, match="must be a list"):
        load_gold({"gold": {"not": "a list"}})


def test_load_gold_bad_type() -> None:
    with pytest.raises(InvalidGoldError, match="list or a mapping"):
        load_gold(42)  # type: ignore[arg-type]


def test_load_gold_schema_invalid() -> None:
    bad = {**_RECORD, "gold_type": "not-a-type"}
    with pytest.raises(InvalidGoldError, match="failed schema validation"):
        load_gold([bad])


def test_load_gold_invalid_field(monkeypatch: pytest.MonkeyPatch) -> None:
    # bypass schema so the domain-object validation (empty classes) is reached
    monkeypatch.setattr(
        "synthaudit_bench.gold.loader.schemas.validate_instance", lambda *a, **k: None
    )
    with pytest.raises(InvalidGoldError, match="invalid field"):
        load_gold([{**_RECORD, "classes": []}])


def test_load_gold_dir(tmp_path: Path) -> None:
    (tmp_path / "d1.json").write_text(json.dumps([_RECORD]), encoding="utf-8")
    (tmp_path / "d2.json").write_text(json.dumps({"gold": [_RECORD]}), encoding="utf-8")
    loaded = load_gold_dir(tmp_path)
    assert set(loaded) == {"d1", "d2"}
    assert len(loaded["d1"]) == 1

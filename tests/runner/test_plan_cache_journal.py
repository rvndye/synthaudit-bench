"""Unit tests for the execution plan, result cache, and completion journal."""

from __future__ import annotations

from pathlib import Path

from _runhelpers import ConstDetector, make_dataset, mapper

from synthaudit_bench.detector import ExecutionContext, run_detector
from synthaudit_bench.runner import (
    FileJournal,
    FileResultCache,
    InMemoryJournal,
    NullCache,
    derive_seed,
    plan_run,
    result_cache_key,
)


def test_derive_seed_is_deterministic_and_varies() -> None:
    assert derive_seed(42, "d-a") == derive_seed(42, "d-a")
    assert derive_seed(42, "d-a") != derive_seed(42, "d-b")
    assert derive_seed(1, "d-a") != derive_seed(2, "d-a")


def test_plan_run_sorts_by_id_and_derives_seed() -> None:
    plan = plan_run([make_dataset("d-c"), make_dataset("d-a"), make_dataset("d-b")])
    assert [item.dataset_id for item in plan] == ["d-a", "d-b", "d-c"]
    assert plan[0].seed == derive_seed(42, "d-a")
    assert plan[0].content_hash == make_dataset("d-a").content_hash()


def test_result_cache_key_stable() -> None:
    key1 = result_cache_key("sha", "det", "1.0", "1.0.0", "cfg")
    key2 = result_cache_key("sha", "det", "1.0", "1.0.0", "cfg")
    key3 = result_cache_key("sha", "det", "1.0", "1.0.0", "other")
    assert key1 == key2
    assert key1 != key3


def test_null_cache_is_always_a_miss() -> None:
    cache = NullCache()
    result = run_detector(ConstDetector(), make_dataset("d"), ExecutionContext(), mapper=mapper())
    cache.put("k", result)
    assert cache.get("k") is None


def test_file_cache_round_trip(tmp_path: Path) -> None:
    cache = FileResultCache(tmp_path / "c")
    result = run_detector(ConstDetector(), make_dataset("d"), ExecutionContext(), mapper=mapper())
    assert cache.get("k") is None  # miss before put
    cache.put("k", result)
    reloaded = cache.get("k")
    assert reloaded is not None
    assert reloaded.dataset_id == "d"
    assert reloaded.content_hash() == result.content_hash()


def test_file_cache_corrupt_entries_are_misses(tmp_path: Path) -> None:
    cache = FileResultCache(tmp_path)
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    (tmp_path / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
    (tmp_path / "partial.json").write_text('{"dataset_id": "x"}', encoding="utf-8")
    assert cache.get("bad") is None
    assert cache.get("list") is None
    assert cache.get("partial") is None


def test_in_memory_journal() -> None:
    journal = InMemoryJournal()
    journal.append("d-a", "h1")
    journal.append("d-b", "h2")
    assert journal.completed() == frozenset({"d-a", "d-b"})


def test_file_journal(tmp_path: Path) -> None:
    journal = FileJournal(tmp_path / "j.jsonl")
    assert journal.completed() == frozenset()  # absent file
    journal.append("d-a", "h1")
    journal.append("d-b", "h2")
    # a blank line in the journal is tolerated
    (tmp_path / "j.jsonl").write_text(
        (tmp_path / "j.jsonl").read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    assert journal.completed() == frozenset({"d-a", "d-b"})

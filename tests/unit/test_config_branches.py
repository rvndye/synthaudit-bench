"""Remaining branch coverage for the configuration subsystem."""

from __future__ import annotations

from synthaudit_bench import config as cfg


def test_expand_dotted_reuses_shared_prefix() -> None:
    # Two dotted keys sharing a prefix exercise the existing-nested-dict path.
    assert cfg.expand_dotted({"a.b": 1, "a.c": 2}) == {"a": {"b": 1, "c": 2}}


def test_parse_env_merges_shared_prefix() -> None:
    parsed = cfg.parse_env({"SAB_LIMITS__WALL_CLOCK_S": "5", "SAB_LIMITS__MEMORY_MB": "9"})
    assert parsed == {"limits": {"wall_clock_s": 5, "memory_mb": 9}}


def test_config_hash_accepts_a_bare_config() -> None:
    resolved = cfg.load_config(env={})
    assert cfg.config_hash(resolved.config) == resolved.config.content_hash()

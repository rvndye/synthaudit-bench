"""Deterministic JSON and JSONL input/output.

All records are serialized through the frozen benchmark canonicalizer
(``synthaudit_bench.canonical.canonical_json``: UTF-8, sorted keys, compact
separators, no BOM), so a given record set always serializes to identical bytes.
Writes are idempotent: writing the same records to the same path yields byte
identical files.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from synthaudit_bench.canonical import canonical_json

from benchkit.errors import InputError, MissingInputError

__all__ = ["read_json", "read_jsonl", "to_canonical_line", "write_json", "write_jsonl"]


def to_canonical_line(record: Any) -> str:
    """Return the deterministic single-line JSON serialization of ``record``."""
    return canonical_json(record).decode("utf-8")


def write_jsonl(path: str | Path, records: Iterable[Any]) -> int:
    """Write ``records`` as canonical JSONL, one object per line. Returns the count.

    Deterministic and idempotent: the same records always produce identical bytes.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [to_canonical_line(record) for record in records]
    target.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return len(lines)


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield each JSON object from a JSONL file. Fails closed if the file is absent."""
    source = Path(path)
    if not source.is_file():
        raise MissingInputError(f"JSONL input not found: {source}")
    for lineno, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InputError(f"{source}:{lineno}: invalid JSON line: {exc}") from exc
        if not isinstance(obj, dict):
            raise InputError(f"{source}:{lineno}: expected a JSON object, got {type(obj).__name__}")
        yield obj


def write_json(path: str | Path, obj: Any) -> None:
    """Write a single object as canonical JSON. Deterministic and idempotent."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(obj) + b"\n")


def read_json(path: str | Path) -> Any:
    """Read a single JSON document. Fails closed if the file is absent."""
    source = Path(path)
    if not source.is_file():
        raise MissingInputError(f"JSON input not found: {source}")
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{source}: invalid JSON: {exc}") from exc

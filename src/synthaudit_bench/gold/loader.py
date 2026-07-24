"""Loading gold tuples from released gold files (specification Section 6.1.2).

Gold for the Evaluation Corpus lives at ``evaluation/gold/<id>.json`` (public-dev
split only). Each record is validated against the normative gold-tuple schema
(Appendix A) at the boundary and parsed into an immutable
:class:`~synthaudit_bench.model.tuples.GoldTuple`; a schema-invalid record fails
closed. Loading reads only the files it is given and never mutates them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.gold.errors import InvalidGoldError
from synthaudit_bench.model.tuples import GoldTuple
from synthaudit_bench.schemas.errors import SchemaValidationError

__all__ = ["load_gold", "load_gold_dir"]


def _build(mapping: Mapping[str, Any]) -> GoldTuple:
    try:
        schemas.validate_instance("gold-tuple", mapping)
    except SchemaValidationError as exc:
        raise InvalidGoldError(f"gold record failed schema validation: {exc}") from exc
    try:
        return GoldTuple.from_mapping(mapping)
    except (ValueError, KeyError) as exc:
        raise InvalidGoldError(f"gold record has an invalid field: {exc}") from exc


def _items(data: Any) -> Sequence[Mapping[str, Any]]:
    if isinstance(data, Mapping):
        for key in ("gold", "tuples", "items"):
            if key in data:
                inner = data[key]
                if isinstance(inner, list):
                    return inner
                raise InvalidGoldError(f"gold field {key!r} must be a list")
        raise InvalidGoldError("gold mapping must carry a 'gold' list")
    if isinstance(data, list):
        return data
    raise InvalidGoldError("gold source must be a list or a mapping with a 'gold' list")


def load_gold(
    source: str | Path | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> tuple[GoldTuple, ...]:
    """Load and validate a dataset's gold tuples from a file, mapping, or list.

    ``source`` may be a path to a JSON file, a decoded mapping carrying a ``gold``
    list, or a list of gold record mappings.

    Raises:
        InvalidGoldError: if a record is schema-invalid or malformed.
    """
    if isinstance(source, (str, Path)):
        data: Any = json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        data = source
    return tuple(_build(item) for item in _items(data))


def load_gold_dir(root: str | Path) -> dict[str, tuple[GoldTuple, ...]]:
    """Load every ``<root>/<id>.json`` gold file, keyed by dataset id (the file stem).

    Files are read in deterministic (sorted) order.

    Raises:
        InvalidGoldError: if any record is schema-invalid or malformed.
    """
    directory = Path(root)
    return {path.stem: load_gold(path) for path in sorted(directory.glob("*.json"))}

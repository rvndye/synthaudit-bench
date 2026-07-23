"""Loading and building a registry: discovery, parsing, validation, indexing.

The loader discovers ``<root>/<corpus>/<id>.yaml`` records in deterministic order,
validates each against the normative dataset schema, parses it into a
``DatasetRecord`` (which enforces the enum vocabularies), assigns its corpus,
split, and content hash, detects duplicate identifiers, and builds an immutable
indexed :class:`Registry`. Loading reads only registry files and an optional
splits and manifest file; results are cached by path. Nothing depends on
filesystem ordering.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from synthaudit_bench import schemas
from synthaudit_bench.model.records import DatasetRecord
from synthaudit_bench.registry.errors import (
    DuplicateIdError,
    IntegrityError,
    InvalidRecordError,
    RegistryError,
)
from synthaudit_bench.registry.model import (
    Corpus,
    Registry,
    RegistryEntry,
    RegistryIndex,
    Split,
)
from synthaudit_bench.schemas.errors import SchemaValidationError

__all__ = ["build_registry", "load_registry"]

_RECORD_GLOB = "*.yaml"
_SPLITS_FILE = ("evaluation", "splits.json")
_MANIFEST_FILE = "MANIFEST.json"


def _index(entries: tuple[RegistryEntry, ...]) -> RegistryIndex:
    by_id: dict[str, RegistryEntry] = {}
    by_corpus: dict[str, list[str]] = {}
    by_split: dict[str, list[str]] = {}
    by_family: dict[str, list[str]] = {}
    by_domain: dict[str, list[str]] = {}
    by_version: dict[str, list[str]] = {}
    by_hash: dict[str, str] = {}
    for entry in entries:
        by_id[entry.id] = entry
        by_corpus.setdefault(entry.corpus.value, []).append(entry.id)
        if entry.split is not None:
            by_split.setdefault(entry.split.value, []).append(entry.id)
        by_family.setdefault(entry.record.generator_family.value, []).append(entry.id)
        by_domain.setdefault(entry.record.domain, []).append(entry.id)
        if entry.record.generator_version is not None:
            by_version.setdefault(entry.record.generator_version, []).append(entry.id)
        if entry.content_hash is not None:
            by_hash[entry.content_hash] = entry.id
    return RegistryIndex(
        by_id=by_id,
        by_corpus={k: tuple(sorted(v)) for k, v in by_corpus.items()},
        by_split={k: tuple(sorted(v)) for k, v in by_split.items()},
        by_generator_family={k: tuple(sorted(v)) for k, v in by_family.items()},
        by_domain={k: tuple(sorted(v)) for k, v in by_domain.items()},
        by_version={k: tuple(sorted(v)) for k, v in by_version.items()},
        by_content_hash=by_hash,
    )


def _parse_record(mapping: Mapping[str, Any]) -> DatasetRecord:
    dataset_id = mapping.get("id", "<unknown>")
    try:
        schemas.validate_instance("dataset", mapping)
    except SchemaValidationError as exc:
        raise InvalidRecordError(f"record {dataset_id!r} failed schema validation: {exc}") from exc
    try:
        return DatasetRecord.from_mapping(mapping)
    except (ValueError, KeyError) as exc:
        raise InvalidRecordError(f"record {dataset_id!r} has an invalid field: {exc}") from exc


def _coerce_split(value: Split | str) -> Split:
    try:
        return Split(value)
    except ValueError as exc:
        raise RegistryError(f"invalid split value: {value!r}") from exc


def build_registry(
    records: Iterable[tuple[Mapping[str, Any], Corpus | str]],
    *,
    splits: Mapping[str, Split | str] | None = None,
    manifest: Mapping[str, str] | None = None,
) -> Registry:
    """Build an immutable registry from parsed record mappings.

    Each record is ``(dataset_mapping, corpus)``. ``splits`` maps a dataset id to
    its split; ``manifest`` maps a dataset id to its canonical content hash. Both
    are optional. Records are schema-validated and parsed; a duplicate identifier
    raises. Entries are ordered deterministically by ``(corpus, id)``.

    Raises:
        InvalidRecordError: if a record is schema-invalid or has an invalid field.
        DuplicateIdError: if two records share an identifier.
    """
    split_map = {k: _coerce_split(v) for k, v in (splits or {}).items()}
    hash_map = dict(manifest or {})
    seen: set[str] = set()
    entries: list[RegistryEntry] = []
    for mapping, corpus_value in records:
        record = _parse_record(mapping)
        if record.id in seen:
            raise DuplicateIdError(f"duplicate dataset id: {record.id!r}")
        seen.add(record.id)
        entries.append(
            RegistryEntry(
                record=record,
                corpus=Corpus(corpus_value),
                split=split_map.get(record.id),
                content_hash=hash_map.get(record.id),
            )
        )
    orphan_splits = sorted(set(split_map) - seen)
    if orphan_splits:
        raise IntegrityError(f"splits reference unknown dataset ids: {orphan_splits}")
    orphan_manifest = sorted(set(hash_map) - seen)
    if orphan_manifest:
        raise IntegrityError(f"manifest references unknown dataset ids: {orphan_manifest}")
    ordered = tuple(sorted(entries, key=lambda e: (e.corpus.value, e.id)))
    return Registry(entries=ordered, index=_index(ordered))


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise InvalidRecordError(f"registry record {path} is not a mapping")
    return dict(loaded)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_splits(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise RegistryError("splits must be a mapping")
    result: dict[str, str] = {}
    if raw and all(isinstance(value, list) for value in raw.values()):
        for split_key, ids in raw.items():
            for dataset_id in ids:
                result[str(dataset_id)] = str(split_key)
    else:
        for dataset_id, split_key in raw.items():
            result[str(dataset_id)] = str(split_key)
    return result


def _normalize_manifest(raw: Any) -> dict[str, str]:
    items: Any = raw
    if isinstance(raw, Mapping) and isinstance(raw.get("datasets"), list):
        items = raw["datasets"]
    result: dict[str, str] = {}
    if isinstance(items, list):
        for entry in items:
            result[str(entry["id"])] = str(entry["sha256"])
    elif isinstance(items, Mapping):
        for dataset_id, value in items.items():
            sha = value["sha256"] if isinstance(value, Mapping) else value
            result[str(dataset_id)] = str(sha)
    else:
        raise RegistryError("manifest must be a mapping or list")
    return result


def _discover_records(root: Path) -> list[tuple[Mapping[str, Any], Corpus]]:
    records: list[tuple[Mapping[str, Any], Corpus]] = []
    for corpus in Corpus:
        directory = root / corpus.value
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(_RECORD_GLOB), key=lambda p: p.name):
            records.append((_read_yaml(path), corpus))
    return records


def _splits_from(
    root: Path, splits: Mapping[str, Split | str] | str | Path | None
) -> dict[str, str]:
    if splits is None:
        candidate = root / _SPLITS_FILE[0] / _SPLITS_FILE[1]
        return _normalize_splits(_read_json(candidate)) if candidate.is_file() else {}
    if isinstance(splits, (str, Path)):
        return _normalize_splits(_read_json(Path(splits)))
    return _normalize_splits(splits)


def _manifest_from(root: Path, manifest: Mapping[str, str] | str | Path | None) -> dict[str, str]:
    if manifest is None:
        candidate = root / _MANIFEST_FILE
        return _normalize_manifest(_read_json(candidate)) if candidate.is_file() else {}
    if isinstance(manifest, (str, Path)):
        return _normalize_manifest(_read_json(Path(manifest)))
    return _normalize_manifest(manifest)


@cache
def _load_cached(root: str, splits: str | None, manifest: str | None) -> Registry:
    root_path = Path(root)
    return build_registry(
        _discover_records(root_path),
        splits=_splits_from(root_path, splits),
        manifest=_manifest_from(root_path, manifest),
    )


def load_registry(
    root: str | Path,
    *,
    splits: Mapping[str, Split | str] | str | Path | None = None,
    manifest: Mapping[str, str] | str | Path | None = None,
    use_cache: bool = True,
) -> Registry:
    """Load and build the registry rooted at ``root``.

    Reads every ``<root>/<corpus>/<id>.yaml`` record, the optional splits file
    (``<root>/evaluation/splits.json`` by default) and manifest file
    (``<root>/MANIFEST.json`` by default), validates and parses each record, and
    returns an immutable indexed :class:`Registry`. Path-based loads are cached.

    Raises:
        InvalidRecordError: if a record is schema-invalid or malformed.
        DuplicateIdError: if two records share an identifier.
        RegistryError: if the splits or manifest source is malformed.
    """
    root_path = Path(root)
    cacheable = use_cache and not isinstance(splits, Mapping) and not isinstance(manifest, Mapping)
    if cacheable:
        splits_key = str(splits) if isinstance(splits, (str, Path)) else None
        manifest_key = str(manifest) if isinstance(manifest, (str, Path)) else None
        return _load_cached(str(root_path), splits_key, manifest_key)
    return build_registry(
        _discover_records(root_path),
        splits=_splits_from(root_path, splits),
        manifest=_manifest_from(root_path, manifest),
    )

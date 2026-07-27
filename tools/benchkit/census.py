"""Deliverable 1: census enumeration pipeline.

Turns human-provided candidate descriptors (the output of the frame query fixed in
``corpus/census/frame.md``) into reproducible census JSONL records. It assigns
stable identifiers, computes an integrity hash over any retrieved bytes, and records
provenance and acquisition metadata. It never enumerates a live source itself, never
annotates, never scores, and never infers a label or a class. Candidates come only
from the caller; if none are supplied, zero records are produced.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from synthaudit_bench.canonical import sha256_bytes

from benchkit.errors import InputError
from benchkit.provenance import provenance_block

__all__ = ["CandidateInput", "CensusRecord", "enumerate_candidates", "stable_id"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def stable_id(source_key: str, *, prefix: str = "census") -> str:
    """Return a deterministic, permanent, kebab-case id for a source key.

    The id is ``<prefix>-<slug>-<8 hex>`` where the slug is the lowercased source
    key and the suffix is the first eight hex characters of its SHA-256, so distinct
    source keys never collide and the same key always maps to the same id.
    """
    if not source_key.strip():
        raise InputError("candidate source_key must be non-empty")
    slug = _SLUG_RE.sub("-", source_key.strip().lower()).strip("-") or "item"
    digest = sha256_bytes(source_key.encode("utf-8"))[:8]
    return f"{prefix}-{slug}-{digest}"


@dataclass(frozen=True, slots=True)
class CandidateInput:
    """One human-provided candidate artifact from the frame query.

    ``source_key`` is a stable identifier from the source repository (used to derive
    the census id). ``file`` is an optional local path to the retrieved bytes; when
    present, an integrity hash is computed over exactly those bytes. Every other
    field is recorded verbatim as supplied and is never inferred.
    """

    source_key: str
    title: str
    source_urls: tuple[str, ...]
    retrieved: str
    file: Path | None = None
    declared_license: str | None = None
    declared_generator_family: str | None = None
    declared_domain: str | None = None
    notes: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CensusRecord:
    """A reproducible census record (tooling metadata, not a registry record)."""

    id: str
    title: str
    source_urls: tuple[str, ...]
    retrieved: str
    file_sha256: str | None
    file_bytes: int | None
    declared: dict[str, Any]
    provenance: dict[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this census record."""
        mapping: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "source_urls": list(self.source_urls),
            "retrieved": self.retrieved,
            "declared": {key: self.declared[key] for key in sorted(self.declared)},
            "provenance": self.provenance,
        }
        if self.file_sha256 is not None:
            mapping["file_sha256"] = self.file_sha256
        if self.file_bytes is not None:
            mapping["file_bytes"] = self.file_bytes
        return mapping


def _declared(candidate: CandidateInput) -> dict[str, Any]:
    declared: dict[str, Any] = dict(candidate.extra)
    if candidate.declared_license is not None:
        declared["license"] = candidate.declared_license
    if candidate.declared_generator_family is not None:
        declared["generator_family"] = candidate.declared_generator_family
    if candidate.declared_domain is not None:
        declared["domain"] = candidate.declared_domain
    if candidate.notes is not None:
        declared["notes"] = candidate.notes
    return declared


def enumerate_candidates(
    candidates: Iterable[CandidateInput],
    *,
    prefix: str = "census",
    generated_at: str | None = None,
) -> list[CensusRecord]:
    """Return census records for ``candidates``, sorted by id.

    Assigns a stable id, computes an integrity hash and byte size over any retrieved
    file, records the declared (verbatim) metadata, and stamps provenance. Raises on
    a duplicate id (two candidates with the same source key), because the census must
    not silently merge duplicates. Produces no output for an empty input.
    """
    records: dict[str, CensusRecord] = {}
    for candidate in candidates:
        cid = stable_id(candidate.source_key, prefix=prefix)
        if cid in records:
            raise InputError(
                f"duplicate census id {cid!r} from source_key {candidate.source_key!r}"
            )
        sha: str | None = None
        size: int | None = None
        if candidate.file is not None:
            path = Path(candidate.file)
            if not path.is_file():
                raise InputError(f"candidate {candidate.source_key!r}: file not found: {path}")
            data = path.read_bytes()
            sha, size = sha256_bytes(data), len(data)
        records[cid] = CensusRecord(
            id=cid,
            title=candidate.title,
            source_urls=tuple(candidate.source_urls),
            retrieved=candidate.retrieved,
            file_sha256=sha,
            file_bytes=size,
            declared=_declared(candidate),
            provenance=provenance_block(
                tool="census.enumerate",
                inputs=[candidate.source_key],
                parameters={"prefix": prefix},
                generated_at=generated_at,
            ),
        )
    return [records[cid] for cid in sorted(records)]


def enumerate_to_mappings(
    candidates: Sequence[CandidateInput],
    *,
    prefix: str = "census",
    generated_at: str | None = None,
) -> list[dict[str, Any]]:
    """Convenience: enumerate and return primitive mappings ready for JSONL."""
    return [
        r.to_mapping()
        for r in enumerate_candidates(candidates, prefix=prefix, generated_at=generated_at)
    ]

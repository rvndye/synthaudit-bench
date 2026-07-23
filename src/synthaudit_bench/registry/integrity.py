"""Referential-integrity checks over a loaded registry.

``referential_integrity`` returns a non-raising report of every violation; it
checks corpus-versus-stratum consistency (census/evaluation separation), split
assignment (every evaluation dataset has a split, no other dataset does),
duplicate content hashes (when hashes are available), and optional schema and
ontology version compatibility. ``validate_registry`` is the fail-closed
convenience that loads (if given a path) and raises on any violation.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from synthaudit_bench import schemas, sto
from synthaudit_bench.errors import VersionError
from synthaudit_bench.model.enums import FrameStratum
from synthaudit_bench.model.semver import Version
from synthaudit_bench.registry.errors import IntegrityError
from synthaudit_bench.registry.loader import load_registry
from synthaudit_bench.registry.model import (
    Corpus,
    IntegrityIssue,
    IntegrityReport,
    Registry,
    Split,
)

__all__ = ["referential_integrity", "validate_registry"]

_EXPECTED_STRATA: dict[Corpus, frozenset[FrameStratum]] = {
    Corpus.CENSUS: frozenset({FrameStratum.CENSUS}),
    Corpus.EVALUATION: frozenset(
        {FrameStratum.PLANTED, FrameStratum.CONTROLLED, FrameStratum.ADJUDICATED_REAL}
    ),
    Corpus.CONTROLLED: frozenset({FrameStratum.CONTROLLED}),
    Corpus.CONFORMANCE: frozenset({FrameStratum.PLANTED, FrameStratum.CONTROLLED}),
}


def _version_supported(required: str, available: tuple[str, ...]) -> bool:
    try:
        wanted = Version.parse(required)
    except VersionError:
        return False
    for candidate in available:
        try:
            if Version.parse(candidate).satisfies(wanted):
                return True
        except VersionError:
            continue
    return False


def referential_integrity(
    registry: Registry,
    *,
    sto_version: str | None = None,
    schema_version: str | None = None,
) -> IntegrityReport:
    """Return a deterministic report of every referential-integrity violation.

    With ``schema_version`` or ``sto_version`` given, the registry's declared
    versions are additionally checked for compatibility against the installed
    schema set and the available ontology versions.
    """
    issues: list[IntegrityIssue] = []
    seen_hash: dict[str, str] = {}
    for entry in registry.entries:
        if entry.record.frame_stratum not in _EXPECTED_STRATA[entry.corpus]:
            issues.append(
                IntegrityIssue(
                    code="corpus_stratum_mismatch",
                    detail=(
                        f"frame_stratum {entry.record.frame_stratum.value!r} is not allowed "
                        f"in corpus {entry.corpus.value!r}"
                    ),
                    dataset_id=entry.id,
                )
            )
        if entry.corpus is Corpus.EVALUATION and entry.split is None:
            issues.append(
                IntegrityIssue("missing_split", "evaluation dataset has no split", entry.id)
            )
        if entry.corpus is not Corpus.EVALUATION and entry.split is not None:
            issues.append(
                IntegrityIssue(
                    code="unexpected_split",
                    detail=f"non-evaluation dataset assigned split {entry.split.value!r}",
                    dataset_id=entry.id,
                )
            )
        if entry.content_hash is not None:
            if entry.content_hash in seen_hash:
                issues.append(
                    IntegrityIssue(
                        code="duplicate_content_hash",
                        detail=f"content hash shared with {seen_hash[entry.content_hash]!r}",
                        dataset_id=entry.id,
                    )
                )
            else:
                seen_hash[entry.content_hash] = entry.id
    if schema_version is not None and not _version_supported(
        schema_version, schemas.supported_versions()
    ):
        issues.append(
            IntegrityIssue(
                code="unsupported_schema_version",
                detail=f"no installed schema version satisfies {schema_version!r}",
            )
        )
    if sto_version is not None and not _version_supported(sto_version, sto.available_versions()):
        issues.append(
            IntegrityIssue(
                code="unavailable_sto_version",
                detail=f"no available ontology version satisfies {sto_version!r}",
            )
        )
    issues.sort(key=lambda issue: (issue.code, issue.dataset_id or ""))
    return IntegrityReport(tuple(issues))


def validate_registry(
    source: Registry | str | Path,
    *,
    splits: Mapping[str, Split | str] | str | Path | None = None,
    manifest: Mapping[str, str] | str | Path | None = None,
    sto_version: str | None = None,
    schema_version: str | None = None,
) -> Registry:
    """Load (if given a path) and fully validate a registry, returning it.

    Raises:
        IntegrityError: if the registry fails any referential-integrity rule.
        RegistryError: if loading a path source fails.
    """
    registry = (
        source
        if isinstance(source, Registry)
        else load_registry(source, splits=splits, manifest=manifest)
    )
    report = referential_integrity(registry, sto_version=sto_version, schema_version=schema_version)
    if not report.ok:
        detail = "; ".join(
            f"[{issue.code}] {issue.dataset_id or ''} {issue.detail}".strip()
            for issue in report.issues
        )
        raise IntegrityError(f"registry failed referential integrity: {detail}")
    return registry

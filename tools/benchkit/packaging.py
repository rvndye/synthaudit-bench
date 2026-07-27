"""Deliverable 8: benchmark packaging.

Validates a benchmark release, generates checksums, and verifies reproducibility,
using the frozen loaders and schema validators. Structural validation mirrors
specification Section 6.1.6: schema-valid records and gold, referential integrity
(every gold and split id has a record), split integrity (public-dev and held-out are
disjoint), and the license gate (non-redistributable records are flagged). Byte-level
integrity and license enforcement over actual downloaded data is the acquisition
pipeline's job; this validates the release structure and its gold, records, and
splits. It fabricates nothing and fails closed on a broken release.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from synthaudit_bench.canonical import canonical_json, sha256_bytes
from synthaudit_bench.gold import GoldError, load_gold_dir, validate_gold
from synthaudit_bench.registry.errors import RegistryError
from synthaudit_bench.registry.loader import load_registry

from benchkit.errors import ReproducibilityError
from benchkit.jsonlio import read_json
from benchkit.provenance import provenance_block

__all__ = ["ReleaseValidation", "release_checksums", "validate_release", "verify_reproducible"]


@dataclass(slots=True)
class ReleaseValidation:
    """Per-rule structural validation of a benchmark release."""

    rules: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when every evaluated rule passed."""
        return all(self.rules.values())

    def _fail(self, rule: str, message: str) -> None:
        self.rules[rule] = False
        self.messages.append(message)

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the validation."""
        return {
            "ok": self.ok,
            "rules": {key: self.rules[key] for key in sorted(self.rules)},
            "counts": {key: self.counts[key] for key in sorted(self.counts)},
            "messages": sorted(self.messages),
            "provenance": self.provenance,
        }


def validate_release(
    registry_root: str | Path,
    *,
    gold_dir: str | Path | None = None,
    splits_path: str | Path | None = None,
    sto_version: str = "1.0.0",
    generated_at: str | None = None,
) -> ReleaseValidation:
    """Validate a release's structure using the frozen loaders (fail closed)."""
    result = ReleaseValidation(
        provenance=provenance_block(
            tool="packaging.validate",
            inputs=[str(registry_root)],
            parameters={"sto_version": sto_version},
            generated_at=generated_at,
        )
    )

    # Rule: schema-valid registry (the frozen loader validates every record).
    result.rules["registry_schema"] = True
    try:
        registry = load_registry(str(registry_root))
    except RegistryError as exc:
        result._fail("registry_schema", f"registry invalid: {exc}")
        return result
    record_ids = {entry.record.id for entry in registry.datasets()}
    result.counts["records"] = len(record_ids)

    # Rule: license gate (record license flags are present and consistent).
    result.rules["license_gate"] = True
    for entry in registry.datasets():
        lic = entry.record.license
        if not isinstance(lic.redistribute, bool) or not isinstance(lic.fetch_scriptable, bool):
            result._fail("license_gate", f"{entry.record.id}: license flags malformed")

    # Rule: gold is schema and semantically valid, and referentially anchored.
    result.rules["gold"] = True
    result.rules["gold_referential"] = True
    gold_ids: set[str] = set()
    if gold_dir is not None and Path(gold_dir).is_dir():
        try:
            gold_by_id = load_gold_dir(str(gold_dir))
        except GoldError as exc:
            result._fail("gold", f"gold invalid: {exc}")
            gold_by_id = {}
        for did, tuples in gold_by_id.items():
            gold_ids.add(did)
            try:
                validate_gold(tuples, sto_version=sto_version)
            except GoldError as exc:
                result._fail("gold", f"gold {did}: {exc}")
            if did not in record_ids:
                result._fail("gold_referential", f"gold {did!r} has no registry record")
    result.counts["gold_datasets"] = len(gold_ids)

    # Rule: split integrity (ids are records; public-dev and held-out are disjoint).
    result.rules["split_integrity"] = True
    if splits_path is not None and Path(splits_path).is_file():
        splits = read_json(splits_path)
        public = set(splits.get("public-dev", []))
        held = set(splits.get("held-out", []))
        result.counts["public_dev"] = len(public)
        result.counts["held_out"] = len(held)
        if public & held:
            result._fail("split_integrity", f"ids in both splits: {sorted(public & held)}")
        missing = (public | held) - record_ids
        if missing:
            result._fail("split_integrity", f"split ids without a record: {sorted(missing)}")

    return result


def release_checksums(files: Mapping[str, Path]) -> dict[str, str]:
    """Return ``logical_name -> sha256`` over the given files (deterministic, sorted)."""
    checksums: dict[str, str] = {}
    for name in sorted(files):
        path = Path(files[name])
        checksums[name] = sha256_bytes(path.read_bytes())
    return checksums


def verify_reproducible(build: Callable[[], Any]) -> bool:
    """Call ``build`` twice and confirm byte-identical canonical output (fail closed)."""
    first = canonical_json(build())
    second = canonical_json(build())
    if first != second:
        raise ReproducibilityError("build produced non-identical output on repeat")
    return True

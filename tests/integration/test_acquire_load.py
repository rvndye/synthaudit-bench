"""End-to-end acquisition and loading: acquire into a cache, then load D = (T, τ, M)."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from synthaudit_bench.acquire import acquire_dataset, verify_source_checksums
from synthaudit_bench.canonical import canonical_csv, sha256_bytes
from synthaudit_bench.load import (
    build_dataset_object,
    infer_column_types,
    load_dataset,
    verify_dataset,
)
from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    ProvenanceConfidence,
    Task,
)
from synthaudit_bench.model.records import (
    DatasetRecord,
    License,
    Loader,
    Source,
    Transparency,
)

pytestmark = pytest.mark.integration


def _canonical_csv_bytes(rows: int = 250) -> bytes:
    lines = ["id,amount,when,grade"]
    for i in range(rows):
        lines.append(f"{1000 + i},{i}.5,2021-01-0{(i % 9) + 1},{'A' if i % 2 else 'B'}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _record(dataset_id: str, digest: str, *, test_split: str | None = None) -> DatasetRecord:
    files = {f"{dataset_id}.csv": digest}
    urls = [f"https://example.org/{dataset_id}.csv"]
    if test_split is not None:
        files[f"{test_split}.csv"] = digest
        urls.append(f"https://example.org/{test_split}.csv")
    return DatasetRecord(
        id=dataset_id,
        title="T",
        frame_stratum=FrameStratum.PLANTED,
        domain="energy",
        generator_family=GeneratorFamily.RULE_BASED,
        provenance_confidence=ProvenanceConfidence.DOCUMENTED,
        task=Task.CLASSIFICATION,
        target="grade",
        license=License(name="CC0 1.0", redistribute=True, fetch_scriptable=True),
        source=Source(urls=tuple(urls), sha256=MappingProxyType(files), retrieved="2026-07-23"),
        loader=Loader(format="csv"),
        transparency=Transparency(True, True, True, True),
        citation="c",
        test_split=test_split,
    )


def test_acquire_then_load_roundtrip(tmp_path: Path) -> None:
    payload = _canonical_csv_bytes()
    digest = sha256_bytes(payload)
    record = _record("grid-01", digest)

    def fetcher(url: str) -> bytes:
        return payload

    acquired = acquire_dataset(record, tmp_path / "cache", fetcher=fetcher, require_data=True)
    assert acquired.verified is True

    # The cached files feed loading directly; loading takes no fetcher (reference-free).
    dataset = load_dataset(record, acquired.files, expected_hash=digest)
    assert dataset.name == "grid-01"
    assert dataset.n_rows == 250
    assert dataset.target == "grade"

    # Identity: the loaded table's canonical CSV hash is the instance identity, and it
    # equals both the acquired-file checksum and a fresh canonical serialization.
    assert dataset.content_hash() == digest
    assert dataset.content_hash() == sha256_bytes(canonical_csv(dataset.table))

    report = verify_dataset(record, acquired.files, expected_content_hash=digest)
    assert report.content_hash == digest


def test_loading_is_deterministic(tmp_path: Path) -> None:
    payload = _canonical_csv_bytes()
    digest = sha256_bytes(payload)
    record = _record("grid-02", digest)
    path = tmp_path / "grid-02.csv"
    path.write_bytes(payload)
    files = {"grid-02.csv": path}

    first = load_dataset(record, files)
    second = load_dataset(record, files)
    assert first.content_hash() == second.content_hash()
    assert first == second
    assert infer_column_types(first.table) == infer_column_types(second.table)


def test_companion_split_end_to_end(tmp_path: Path) -> None:
    payload = _canonical_csv_bytes(rows=210)
    digest = sha256_bytes(payload)
    record = _record("grid-03", digest, test_split="grid-03-holdout")
    primary = tmp_path / "grid-03.csv"
    holdout = tmp_path / "grid-03-holdout.csv"
    primary.write_bytes(payload)
    holdout.write_bytes(payload)
    files = {"grid-03.csv": primary, "grid-03-holdout.csv": holdout}

    verify_source_checksums(record, files)
    dataset = load_dataset(record, files)
    assert dataset.has_test is True
    assert dataset.test_table is not None
    assert dataset.test_table.shape[0] == 210


def test_build_dataset_object_identity_independent_of_typing(tmp_path: Path) -> None:
    # Typing and normalization are analysis-only; they do not change stored identity.
    payload = _canonical_csv_bytes()
    digest = sha256_bytes(payload)
    record = _record("grid-04", digest)
    path = tmp_path / "grid-04.csv"
    path.write_bytes(payload)

    dataset = load_dataset(record, {"grid-04.csv": path})
    rebuilt = build_dataset_object(record, dataset.table)
    assert rebuilt.content_hash() == digest  # identity survives a rebuild
    _ = infer_column_types(dataset.table)  # does not mutate the table
    assert dataset.content_hash() == digest

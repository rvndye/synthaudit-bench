"""Unit tests for the acquisition subsystem: cache, fetch stubs, integrity gate."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from synthaudit_bench import acquire
from synthaudit_bench.acquire import (
    AcquiredDataset,
    ChecksumError,
    FetchStub,
    LicenseError,
    ResourceError,
    _url_for,
    acquire_dataset,
    cache_path,
    fetch_stub,
    verify_source_checksums,
)
from synthaudit_bench.canonical import sha256_bytes
from synthaudit_bench.load import MissingFileError
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

_PAYLOAD = b"id,a,b,c\n1,2,3,4\n"
_DIGEST = sha256_bytes(_PAYLOAD)


def _record(
    dataset_id: str = "ds-a",
    *,
    sha: dict[str, str] | None = None,
    urls: tuple[str, ...] | None = None,
    fetch_scriptable: bool = True,
    redistribute: bool = True,
) -> DatasetRecord:
    filename = f"{dataset_id}.csv"
    return DatasetRecord(
        id=dataset_id,
        title="T",
        frame_stratum=FrameStratum.PLANTED,
        domain="energy",
        generator_family=GeneratorFamily.RULE_BASED,
        provenance_confidence=ProvenanceConfidence.DOCUMENTED,
        task=Task.CLASSIFICATION,
        target="c",
        license=License(
            name="CC0 1.0",
            redistribute=redistribute,
            fetch_scriptable=fetch_scriptable,
            spdx="CC0-1.0",
        ),
        source=Source(
            urls=urls if urls is not None else (f"https://example.org/{filename}",),
            sha256=MappingProxyType(sha if sha is not None else {filename: _DIGEST}),
            retrieved="2026-07-23",
        ),
        loader=Loader(format="csv"),
        transparency=Transparency(True, True, True, True),
        citation="c",
    )


def _write(path: Path, data: bytes = _PAYLOAD) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


# --------------------------------------------------------------------------- #
# cache_path                                                                   #
# --------------------------------------------------------------------------- #


def test_cache_path_composes_deterministically() -> None:
    assert cache_path("/cache", "ds-a", "ds-a.csv") == Path("/cache/ds-a/ds-a.csv")


@pytest.mark.parametrize("bad", ["a/b.csv", "a\\b.csv", "", ".", ".."])
def test_cache_path_rejects_unsafe_filenames(bad: str) -> None:
    with pytest.raises(ResourceError, match="unsafe cache filename"):
        cache_path("/cache", "ds-a", bad)


# --------------------------------------------------------------------------- #
# fetch_stub                                                                   #
# --------------------------------------------------------------------------- #


def test_fetch_stub_projects_provenance_and_license() -> None:
    record = _record(fetch_scriptable=False, redistribute=False)
    stub = fetch_stub(record, reason="why")
    assert isinstance(stub, FetchStub)
    assert stub.dataset_id == "ds-a"
    assert stub.urls == ("https://example.org/ds-a.csv",)
    assert stub.sha256["ds-a.csv"] == _DIGEST
    assert stub.license_name == "CC0 1.0"
    assert stub.redistribute is False
    assert stub.fetch_scriptable is False
    assert stub.reason == "why"
    assert stub.to_mapping()["sha256"] == {"ds-a.csv": _DIGEST}


# --------------------------------------------------------------------------- #
# verify_source_checksums                                                      #
# --------------------------------------------------------------------------- #


def test_verify_source_checksums_ok(tmp_path: Path) -> None:
    record = _record()
    files = {"ds-a.csv": _write(tmp_path / "ds-a.csv")}
    assert verify_source_checksums(record, files) == ("ds-a.csv",)


def test_verify_source_checksums_empty_is_resource_error() -> None:
    record = _record(sha={})
    with pytest.raises(ResourceError, match="no source checksums"):
        verify_source_checksums(record, {})


def test_verify_source_checksums_missing_file() -> None:
    with pytest.raises(MissingFileError, match="missing required file"):
        verify_source_checksums(_record(), {})


def test_verify_source_checksums_mismatch(tmp_path: Path) -> None:
    record = _record(sha={"ds-a.csv": "0" * 64})
    files = {"ds-a.csv": _write(tmp_path / "ds-a.csv")}
    with pytest.raises(ChecksumError, match="does not match declared"):
        verify_source_checksums(record, files)


def test_verify_source_checksums_directory_not_file(tmp_path: Path) -> None:
    (tmp_path / "ds-a.csv").mkdir()
    with pytest.raises(MissingFileError):
        verify_source_checksums(_record(), {"ds-a.csv": tmp_path / "ds-a.csv"})


# --------------------------------------------------------------------------- #
# _url_for                                                                     #
# --------------------------------------------------------------------------- #


def test_url_for_endswith_single_match() -> None:
    assert _url_for("x.csv", ("http://a/x.csv", "http://b/y.csv")) == "http://a/x.csv"


def test_url_for_single_url_no_match() -> None:
    assert _url_for("x.csv", ("http://a/download?id=7",)) == "http://a/download?id=7"


def test_url_for_substring_single_match() -> None:
    assert _url_for("x.csv", ("http://a/get?f=x.csv&v=1", "http://b/other")) == (
        "http://a/get?f=x.csv&v=1"
    )


def test_url_for_ambiguous_raises() -> None:
    with pytest.raises(ResourceError, match="unique source URL"):
        _url_for("x.csv", ("http://a/x.csv", "http://b/x.csv"))


def test_url_for_no_match_multiple_urls_raises() -> None:
    with pytest.raises(ResourceError, match="unique source URL"):
        _url_for("x.csv", ("http://a/y", "http://b/z"))


# --------------------------------------------------------------------------- #
# acquire_dataset                                                             #
# --------------------------------------------------------------------------- #


def test_acquire_fetches_and_verifies(tmp_path: Path) -> None:
    record = _record()
    calls: list[str] = []

    def fetcher(url: str) -> bytes:
        calls.append(url)
        return _PAYLOAD

    result = acquire_dataset(record, tmp_path / "cache", fetcher=fetcher, require_data=True)
    assert isinstance(result, AcquiredDataset)
    assert result.verified is True
    assert result.is_stub is False
    assert calls == ["https://example.org/ds-a.csv"]
    assert result.files["ds-a.csv"].read_bytes() == _PAYLOAD


def test_acquire_is_idempotent_over_verified_cache(tmp_path: Path) -> None:
    record = _record()
    calls: list[str] = []

    def fetcher(url: str) -> bytes:
        calls.append(url)
        return _PAYLOAD

    cache = tmp_path / "cache"
    acquire_dataset(record, cache, fetcher=fetcher)
    second = acquire_dataset(record, cache, fetcher=fetcher)
    assert len(calls) == 1  # the verified cache hit did not re-fetch
    assert second.verified is True


def test_acquire_corrupt_cache_refetches_when_fetcher_available(tmp_path: Path) -> None:
    record = _record()
    cache = tmp_path / "cache"
    _write(cache_path(cache, "ds-a", "ds-a.csv"), b"corrupt")

    def fetcher(url: str) -> bytes:
        return _PAYLOAD

    result = acquire_dataset(record, cache, fetcher=fetcher, require_data=True)
    assert result.verified is True
    assert result.files["ds-a.csv"].read_bytes() == _PAYLOAD


def test_acquire_corrupt_cache_without_fetcher_fails_closed(tmp_path: Path) -> None:
    record = _record()
    cache = tmp_path / "cache"
    _write(cache_path(cache, "ds-a", "ds-a.csv"), b"corrupt")
    with pytest.raises(ChecksumError):
        acquire_dataset(record, cache)


def test_acquire_fetched_checksum_mismatch_deletes_and_raises(tmp_path: Path) -> None:
    record = _record(sha={"ds-a.csv": "0" * 64})
    cache = tmp_path / "cache"

    def fetcher(url: str) -> bytes:
        return _PAYLOAD

    with pytest.raises(ChecksumError, match="does not match declared"):
        acquire_dataset(record, cache, fetcher=fetcher)
    assert not cache_path(cache, "ds-a", "ds-a.csv").exists()  # corrupt file removed


def test_acquire_fetcher_exception_is_resource_error(tmp_path: Path) -> None:
    record = _record()

    def fetcher(url: str) -> bytes:
        raise OSError("network down")

    with pytest.raises(ResourceError, match="failed"):
        acquire_dataset(record, tmp_path / "cache", fetcher=fetcher)


def test_acquire_license_gate_returns_stub(tmp_path: Path) -> None:
    record = _record(fetch_scriptable=False, redistribute=False)
    result = acquire_dataset(record, tmp_path / "cache")
    assert result.is_stub is True
    assert result.verified is False
    assert result.stub is not None
    assert "license" in result.stub.reason


def test_acquire_license_gate_required_raises(tmp_path: Path) -> None:
    record = _record(fetch_scriptable=False)
    with pytest.raises(LicenseError, match="forbids scripted fetch"):
        acquire_dataset(record, tmp_path / "cache", require_data=True)


def test_acquire_no_fetcher_returns_stub(tmp_path: Path) -> None:
    result = acquire_dataset(_record(), tmp_path / "cache")
    assert result.is_stub is True
    assert result.stub is not None
    assert "no fetcher" in result.stub.reason


def test_acquire_no_fetcher_required_raises(tmp_path: Path) -> None:
    with pytest.raises(ResourceError, match="no fetcher"):
        acquire_dataset(_record(), tmp_path / "cache", require_data=True)


def test_acquire_empty_checksums_returns_stub(tmp_path: Path) -> None:
    result = acquire_dataset(_record(sha={}), tmp_path / "cache")
    assert result.is_stub is True
    assert result.stub is not None
    assert "no source files" in result.stub.reason


def test_acquire_empty_checksums_required_raises(tmp_path: Path) -> None:
    with pytest.raises(ResourceError, match="no source files"):
        acquire_dataset(_record(sha={}), tmp_path / "cache", require_data=True)


# --------------------------------------------------------------------------- #
# result mappings                                                             #
# --------------------------------------------------------------------------- #


def test_acquired_dataset_to_mapping_verified(tmp_path: Path) -> None:
    record = _record()

    def fetcher(url: str) -> bytes:
        return _PAYLOAD

    result = acquire_dataset(record, tmp_path / "cache", fetcher=fetcher)
    mapping = result.to_mapping()
    assert mapping["verified"] is True
    assert mapping["is_stub"] is False
    assert "stub" not in mapping
    assert set(mapping["files"]) == {"ds-a.csv"}


def test_acquired_dataset_to_mapping_stub(tmp_path: Path) -> None:
    result = acquire_dataset(_record(), tmp_path / "cache")
    mapping = result.to_mapping()
    assert mapping["is_stub"] is True
    assert mapping["files"] == {}
    assert mapping["stub"]["dataset_id"] == "ds-a"


def test_acquire_error_hierarchy() -> None:
    for exc in (ResourceError, ChecksumError, LicenseError):
        assert issubclass(exc, acquire.AcquireError)

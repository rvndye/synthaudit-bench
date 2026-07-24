"""Dataset acquisition: fetch stubs, local cache, and fail-closed integrity.

This is the benchmark's acquisition subsystem and the *only* component permitted
to reach an external resource (specification Section 5.1: an auditing
implementation "MUST NOT access any resource other than D and T'"). Acquisition
is deliberately isolated here so that loading, detection, and scoring can never
touch the network.

Network access is optional and fully injected. This module never imports an HTTP
client, opens a socket, or consults a clock or a global. A caller that wants
scripted fetching passes a :data:`Fetcher` (a ``Callable[[str], bytes]``); with
no fetcher, acquisition is a pure local-cache-and-verify operation. Every file
obtained is checked against the record's declared SHA-256 before it is trusted,
and a mismatch fails closed: the offending file is removed and a
:class:`ChecksumError` is raised (specification Sections 6.1.5, 9 step 1).

Datasets whose license forbids scripted fetching participate as *fetch stubs*
(specification Section 6.1.4): the acquisition result carries the source URLs and
expected hashes instead of data, so a downstream user can obtain the files
manually under the license.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from synthaudit_bench.canonical import sha256_bytes
from synthaudit_bench.errors import SynthAuditBenchError
from synthaudit_bench.model.records import DatasetRecord

__all__ = [
    "AcquireError",
    "AcquiredDataset",
    "ChecksumError",
    "FetchStub",
    "Fetcher",
    "LicenseError",
    "ResourceError",
    "acquire_dataset",
    "cache_path",
    "fetch_stub",
    "verify_source_checksums",
]

Fetcher = Callable[[str], bytes]
"""A byte-returning fetch function ``(url) -> bytes`` injected by the caller.

Acquisition ships no implementation of this protocol. Keeping the transport
outside the library is what guarantees that no benchmark component fetches a
resource unless the caller explicitly wires one in.
"""


class AcquireError(SynthAuditBenchError):
    """A dataset could not be acquired.

    Base class for every acquisition failure so callers can handle the whole
    subsystem exhaustively.
    """


class ResourceError(AcquireError):
    """A required external resource could not be obtained.

    Raised when data is absent from the cache and cannot be fetched (no fetcher
    was provided, the fetch transport failed, or a source URL could not be
    resolved). Corresponds to the ``resource`` failure code of specification
    Section 5.9 (E-4).
    """


class ChecksumError(AcquireError):
    """A file's bytes do not match its declared SHA-256 (an integrity failure).

    Acquisition fails closed on this error: a fetched file that fails its
    checksum is deleted before the error propagates, and a corrupt cache entry
    is never returned as verified (specification Sections 6.1.5 and 9 step 1).
    """


class LicenseError(AcquireError):
    """The dataset's license forbids the requested acquisition.

    Raised when data is required but the license does not permit scripted
    fetching (``fetch_scriptable`` is false); such datasets participate as fetch
    stubs instead (specification Section 6.1.4).
    """


@dataclass(frozen=True, slots=True)
class FetchStub:
    """A fetch specification standing in for non-redistributable data.

    Carries everything a downstream user needs to obtain the files themselves
    under the dataset's license: the source URLs, the expected per-file SHA-256
    hashes, and the license terms (specification Section 6.1.4).
    """

    dataset_id: str
    urls: tuple[str, ...]
    sha256: Mapping[str, str]
    license_name: str
    redistribute: bool
    fetch_scriptable: bool
    retrieved: str
    reason: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this stub."""
        return {
            "dataset_id": self.dataset_id,
            "urls": list(self.urls),
            "sha256": {name: self.sha256[name] for name in sorted(self.sha256)},
            "license_name": self.license_name,
            "redistribute": self.redistribute,
            "fetch_scriptable": self.fetch_scriptable,
            "retrieved": self.retrieved,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AcquiredDataset:
    """The outcome of acquiring a dataset: either verified files or a stub.

    When :attr:`is_stub` is false, :attr:`files` maps each declared filename to
    its verified path in the cache and :attr:`verified` is true. When
    :attr:`is_stub` is true, no data was obtained and :attr:`stub` describes how
    to fetch it manually.
    """

    dataset_id: str
    files: Mapping[str, Path]
    verified: bool
    is_stub: bool
    stub: FetchStub | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this result."""
        mapping: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "files": {name: str(self.files[name]) for name in sorted(self.files)},
            "verified": self.verified,
            "is_stub": self.is_stub,
        }
        if self.stub is not None:
            mapping["stub"] = self.stub.to_mapping()
        return mapping


def cache_path(cache_dir: str | Path, dataset_id: str, filename: str) -> Path:
    """Return the deterministic cache location ``<cache_dir>/<dataset_id>/<filename>``.

    The mapping from (cache directory, dataset, file) to path is pure, so a
    second acquisition into the same cache directory addresses exactly the same
    files. The filename must be a single path component; a filename containing a
    path separator is rejected to keep cached files inside the dataset directory.
    """
    if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
        raise ResourceError(f"unsafe cache filename: {filename!r}")
    return Path(cache_dir) / dataset_id / filename


def fetch_stub(record: DatasetRecord, *, reason: str = "") -> FetchStub:
    """Build the fetch stub for ``record`` from its source and license metadata.

    The stub is a faithful projection of the record's provenance: the same
    source URLs, the same per-file expected hashes, and the same license terms
    (specification Section 6.1.4). It never touches the network.
    """
    source = record.source
    return FetchStub(
        dataset_id=record.id,
        urls=tuple(source.urls),
        sha256=MappingProxyType(dict(source.sha256)),
        license_name=record.license.name,
        redistribute=record.license.redistribute,
        fetch_scriptable=record.license.fetch_scriptable,
        retrieved=source.retrieved,
        reason=reason,
    )


def verify_source_checksums(record: DatasetRecord, files: Mapping[str, Path]) -> tuple[str, ...]:
    """Verify each declared source file against its expected SHA-256, fail-closed.

    Every filename in ``record.source.sha256`` must be present in ``files`` and
    its bytes must hash to the declared value (compared case-insensitively). The
    check reads only the given files and never mutates them.

    Returns:
        The verified filenames, sorted.

    Raises:
        MissingFileError: if a declared file is absent from ``files``.
        ChecksumError: if a present file's bytes do not match its declared hash.
    """
    from synthaudit_bench.load import MissingFileError

    expected = record.source.sha256
    if not expected:
        raise ResourceError(f"record {record.id!r} declares no source checksums")
    verified: list[str] = []
    for name in sorted(expected):
        path = files.get(name)
        if path is None or not path.is_file():
            raise MissingFileError(f"dataset {record.id!r}: missing required file {name!r}")
        actual = sha256_bytes(path.read_bytes())
        if actual != expected[name].lower():
            raise ChecksumError(
                f"dataset {record.id!r}: file {name!r} hash {actual} "
                f"does not match declared {expected[name].lower()}"
            )
        verified.append(name)
    return tuple(verified)


def _url_for(name: str, urls: tuple[str, ...]) -> str:
    """Resolve the source URL that supplies file ``name`` deterministically."""
    matches = [url for url in urls if url.rstrip("/").endswith(name)]
    if len(matches) == 1:
        return matches[0]
    if not matches and len(urls) == 1:
        return urls[0]
    substring = [url for url in urls if name in url]
    if len(substring) == 1:
        return substring[0]
    raise ResourceError(f"cannot resolve a unique source URL for file {name!r}")


def _cached_files(cache_dir: Path, record: DatasetRecord) -> dict[str, Path]:
    return {name: cache_path(cache_dir, record.id, name) for name in record.source.sha256}


def _fetch_and_verify(record: DatasetRecord, fetcher: Fetcher, cache_dir: Path) -> dict[str, Path]:
    urls = tuple(record.source.urls)
    obtained: dict[str, Path] = {}
    for name in sorted(record.source.sha256):
        expected = record.source.sha256[name].lower()
        url = _url_for(name, urls)
        try:
            data = fetcher(url)
        except Exception as exc:
            # Any transport failure (the fetcher is caller-supplied) is a resource failure.
            raise ResourceError(f"dataset {record.id!r}: fetching {url!r} failed: {exc}") from exc
        actual = sha256_bytes(data)
        destination = cache_path(cache_dir, record.id, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if actual != expected:
            destination.unlink(missing_ok=True)
            raise ChecksumError(
                f"dataset {record.id!r}: fetched {name!r} hash {actual} "
                f"does not match declared {expected}"
            )
        obtained[name] = destination
    return obtained


def acquire_dataset(
    record: DatasetRecord,
    cache_dir: str | Path,
    *,
    fetcher: Fetcher | None = None,
    require_data: bool = False,
) -> AcquiredDataset:
    """Acquire ``record``'s data into ``cache_dir``, returning files or a stub.

    Acquisition is idempotent and deterministic: if every declared file is
    already cached and verifies, no fetch is attempted and the cached paths are
    returned. Otherwise the license gate is applied first (a non-scriptable
    license yields a fetch stub, or a :class:`LicenseError` when ``require_data``
    is set), then, if a ``fetcher`` is supplied, each file is fetched, written to
    the cache, and verified against its declared SHA-256 (fail-closed). With no
    fetcher and missing data, a stub is returned, or a :class:`ResourceError` is
    raised when ``require_data`` is set. This is the sole network-capable entry
    point in the library, and only when the caller injects ``fetcher``.

    Args:
        record: The dataset metadata record (its ``source`` and ``license``
            drive acquisition).
        cache_dir: The local cache root; files land under ``<cache_dir>/<id>/``.
        fetcher: An optional injected ``(url) -> bytes`` transport. When ``None``
            acquisition is local-only.
        require_data: When true, an outcome that would be a stub instead raises
            (``LicenseError`` or ``ResourceError``).

    Raises:
        ResourceError: if data is required but cannot be obtained.
        LicenseError: if data is required but the license forbids scripted fetch.
        ChecksumError: if obtained bytes fail their declared checksum.
    """
    cache_root = Path(cache_dir)
    checksums = record.source.sha256
    if not checksums:
        if require_data:
            raise ResourceError(f"record {record.id!r} declares no source files to acquire")
        return AcquiredDataset(
            record.id,
            MappingProxyType({}),
            verified=False,
            is_stub=True,
            stub=fetch_stub(record, reason="record declares no source files"),
        )

    cached = _cached_files(cache_root, record)
    if all(path.is_file() for path in cached.values()):
        try:
            verify_source_checksums(record, cached)
        except ChecksumError:
            if fetcher is None:
                raise
        else:
            return AcquiredDataset(
                record.id, MappingProxyType(dict(cached)), verified=True, is_stub=False
            )

    if not record.license.fetch_scriptable:
        if require_data:
            raise LicenseError(
                f"dataset {record.id!r}: license {record.license.name!r} forbids scripted fetch"
            )
        return AcquiredDataset(
            record.id,
            MappingProxyType({}),
            verified=False,
            is_stub=True,
            stub=fetch_stub(record, reason="license forbids scripted fetch"),
        )

    if fetcher is None:
        if require_data:
            raise ResourceError(
                f"dataset {record.id!r}: data not cached and no fetcher was provided"
            )
        return AcquiredDataset(
            record.id,
            MappingProxyType({}),
            verified=False,
            is_stub=True,
            stub=fetch_stub(record, reason="data not cached and no fetcher provided"),
        )

    obtained = _fetch_and_verify(record, fetcher, cache_root)
    return AcquiredDataset(record.id, MappingProxyType(obtained), verified=True, is_stub=False)

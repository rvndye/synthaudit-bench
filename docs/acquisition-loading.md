# Acquisition and loading

The `synthaudit_bench.acquire` and `synthaudit_bench.load` modules turn declarative
dataset metadata and on-disk files into the immutable dataset object `D = (T, τ, M)`
that every detector consumes. Acquisition obtains and checksums the files;
loading reads them faithfully into a typed table and verifies the instance
identity. The two are deliberately separate, because the specification draws a
hard line around external access: an auditing implementation "MUST NOT access any
resource other than D and T'" (Section 5.1). Acquisition is the one component
allowed to reach outside the process, and even it does so only when the caller
injects a transport.

## The isolation boundary

`acquire` is the sole network-capable module, and it ships no network code. It
never imports an HTTP client, opens a socket, or consults a clock or a global.
Scripted fetching happens only through an injected `Fetcher`, a plain
`Callable[[str], bytes]` the caller supplies; with no fetcher, acquisition is a
pure local-cache-and-verify operation. `load` has no notion of a URL at all: it
reads only the files it is handed. This keeps the reference-free premise
structurally enforceable rather than merely documented, and it means loading,
typing, normalization, and detection can never accidentally retrieve the real
source data or a generator.

## Acquisition

`acquire_dataset` obtains a dataset's declared files into a local cache and
returns an `AcquiredDataset`. It is idempotent and deterministic: the cache
location of every file is a pure function of the cache directory, the dataset id,
and the filename (`cache_path`), so a second acquisition into the same directory
addresses exactly the same files. When every declared file is already cached and
verifies against its recorded SHA-256, no fetch is attempted and the cached paths
are returned unchanged.

When data is missing, acquisition applies the license gate first. A dataset whose
license does not permit scripted fetching (`fetch_scriptable` is false) never
triggers a download; it yields a **fetch stub** instead (Section 6.1.4). A
`FetchStub` is a faithful projection of the record's provenance, carrying the
source URLs, the expected per-file hashes, and the license terms, so a downstream
user can obtain the files manually under the license. If the caller sets
`require_data=True`, a would-be stub is promoted to a raised error instead
(`LicenseError` for the license gate, `ResourceError` when no fetcher is available
or the data simply cannot be obtained), so a pipeline that truly needs the bytes
fails loudly rather than proceeding on a stub.

Every obtained file is checksummed before it is trusted, and a mismatch fails
closed. A file fetched with the wrong bytes is deleted before the `ChecksumError`
propagates, so a corrupt download is never left in the cache; a cache entry that
has silently rotted is re-fetched when a fetcher is available and otherwise raises
rather than being returned as verified. `verify_source_checksums` exposes the same
fail-closed file-integrity check on its own.

```python
from synthaudit_bench.acquire import acquire_dataset

def fetcher(url: str) -> bytes:          # caller-supplied transport
    ...                                  # (requests, urllib, a test double, ...)

acquired = acquire_dataset(record, cache_dir="~/.cache/sab",
                           fetcher=fetcher, require_data=True)
assert acquired.verified
table_paths = acquired.files             # filename -> verified cache path
```

## Loading

`load_dataset` reads the canonical CSV form of Section 6.1.3 into an immutable
`DatasetObject`. Reading is faithful by construction: every cell is read as text
with automatic NA-coercion disabled, so an empty cell, the literal `NA`, and a
value like `1.50` all survive verbatim. Because the table is preserved exactly, it
re-serializes to the canonical bytes it came from, and the object's content hash
therefore equals the SHA-256 instance identity recorded in the release manifest.
When `expected_hash` is supplied, that identity is checked and a mismatch fails
closed (Section 9, step 1). If the record names a companion table through
`test_split`, the corresponding `T'` is loaded alongside `T`; `load_companion_split`
loads only the companion, for the cross-split contamination check (STO-R02).

`build_dataset_object` assembles the `DatasetObject` from a record and a table,
taking the name and target from the record. A target column that the metadata
declares but the table does not contain is a metadata/table inconsistency and
raises an `IngestError` rather than producing a malformed object.

Logical typing and missing-value handling are analysis operations over the loaded
table, not transformations baked into it. This matters for identity: normalization
and typing must never change the stored, hashable table. `infer_column_types`
implements Appendix D.5 over each column's non-missing cells, in a fixed
precedence so the result never depends on row or column order: a column is
`numeric` if every cell parses as a finite real; otherwise `datetime` if every
cell parses as ISO-8601; otherwise `identifier` if the distinct-value ratio
exceeds 0.5 and the distinct count exceeds 1000; otherwise `categorical`, which is
also the type of an all-missing column. `normalize_missing_values` returns a copy
in which the normative missing markers (empty string, `NA`, `NaN`, `null`;
Section 5.2 N2) are collapsed to a single NA sentinel, leaving the input
untouched. `below_minimum` reports whether a table falls under the scorable floor
of 200 rows and 4 columns, which a harness surfaces as `below_minimum`.

```python
from synthaudit_bench.load import load_dataset, infer_column_types, below_minimum

dataset = load_dataset(record, acquired.files, expected_hash=manifest_sha)
types = infer_column_types(dataset.table)     # {column: LogicalType}
too_small = below_minimum(dataset.table)      # bool
```

## Verification

`verify_dataset` is the comprehensive, fail-closed integrity gate. In order, it
validates the record against the normative `dataset` schema, confirms every
declared source file is present and matches its SHA-256, parses the primary table
(and the companion split when declared) from canonical CSV, checks that a declared
target column exists in the table, and, when given an expected content hash,
confirms the canonical instance identity. The first violation raises a structured
error; a `VerificationReport` is returned only when every rule passes. This is the
per-dataset ingestion check of the evaluation protocol (Sections 6.1.5, 6.1.6, and
9 steps 1 to 2).

## Errors

Every failure is a subclass of `SynthAuditBenchError`, so callers can handle the
subsystem exhaustively. Acquisition raises `ResourceError` (a required external
resource could not be obtained; the `resource` failure of Section 5.9),
`ChecksumError` (bytes do not match a declared hash; an integrity failure), and
`LicenseError` (the license forbids the requested acquisition). Loading raises
`IngestError` and its subtypes `InvalidMetadataError` (the record fails schema
validation), `UnsupportedFormatError` (a non-CSV canonical format was requested),
and `MissingFileError` (a required file is absent). A malformed file surfaces as
an `IngestError`, and a checksum or content-hash failure as a `ChecksumError`,
never as a silent partial result.

## Public API

Acquisition: `acquire_dataset`, `fetch_stub`, `verify_source_checksums`,
`cache_path`, and the `AcquiredDataset`, `FetchStub`, and `Fetcher` types.
Loading: `load_dataset`, `build_dataset_object`, `load_companion_split`,
`verify_dataset`, `infer_column_types`, `normalize_missing_values`,
`below_minimum`, and the `LogicalType`, `VerificationReport` types. Every function
is detector-independent, reads only its inputs, and (in `load`) performs no
external access whatsoever.

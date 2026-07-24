# Execution engine

The `synthaudit_bench.runner` package runs one detector over a set of datasets and
assembles the reproducibility manifest (architecture Section 7). It is built so
that outputs never depend on scheduling: datasets are planned in a fixed
sorted-by-id order with deterministically derived per-dataset seeds, and every
result is ordered by dataset id, so a serial run and a parallel run of the same
inputs produce identical results and an identical manifest hash.

## Planning

`plan_run` turns datasets into an ordered tuple of `WorkItem`s, sorted by dataset
id. Each item carries the dataset's content hash (its instance identity) and a
per-dataset seed from `derive_seed(root_seed, dataset_id)` (the top bits of a
SHA-256), so a detector's pseudo-randomness is reproducible and independent of
which worker runs it or in what order.

## Running

`run_benchmark` executes the plan and returns a `RunOutcome` with the ordered
results, the `RunManifest`, and a structured event log. Execution is fail-open per
dataset: each dataset is run through `run_detector`, which isolates any detector
failure into a structured `ErrorRecord`, so one dataset's failure never stops the
batch. Execution is fail-closed on integrity: if a dataset's content hash
contradicts a supplied expected hash, the run aborts with `IntegrityAbort`.

Concurrency is optional (`jobs > 1` uses a thread pool) and does not change
semantics: each dataset's result is computed independently, results are collected
and then sorted by dataset id, and the shared cache and journal are written from a
single thread in that order. Cancellation is cooperative: when `should_cancel`
returns true, the remaining datasets are recorded as `cancelled` rather than run.

## Caching and resuming

An optional content-addressed `ResultCache` keys each result by the SHA-256 of the
dataset content hash, the detector name and version, the ontology version, and the
config hash (`result_cache_key`), so re-running with unchanged inputs reuses
results and a resumed run skips completed datasets. Reads are corruption-checked: a
cache entry that will not parse back into an `AuditResult` is a miss. Because the
key is content-addressed, two datasets with byte-identical tables share an entry;
the reused result is relabeled with the current dataset id so per-dataset
provenance stays correct. An append-only `Journal` records `{dataset_id,
result_hash}` per completed dataset for crash recovery.

## The manifest and artifacts

At completion the runner assembles the `RunManifest` (specification Section 9.6):
the benchmark, ontology, and schema versions, the detector identity, the config
hash, the environment (captured without a clock via `capture_environment`), the
root seed, the resource limits in force, per-dataset content hashes and statuses,
and the run timestamps. Timestamps and the environment are injected at this
supervisor boundary, and timestamps are excluded from the manifest's content hash,
so two runs producing identical results hash identically regardless of when they
ran. `write_artifacts` writes `audits/<dataset_id>.json` per result and
`manifest.json`. The manifest is validated against the run-manifest schema before
it is returned.

## Public API

`run_benchmark`, `RunOutcome`, `RunEvent`; `plan_run`, `WorkItem`, `derive_seed`;
`ResultCache`, `NullCache`, `FileResultCache`, `result_cache_key`; `Journal`,
`InMemoryJournal`, `FileJournal`; `capture_environment`, `write_artifacts`,
`run_id`; and `IntegrityAbort`.

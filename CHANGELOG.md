# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The **software**
package follows [Semantic Versioning](https://semver.org/); the **benchmark**
(corpus, ontology, specification) is versioned independently per `GOVERNANCE.md`.

## [Unreleased]

### Added
- WP8 Detector protocol and normalization: the `detector` subsystem, the
  tool-agnostic seam any structural auditing system implements to be scored. A
  stable `Detector` protocol (`capabilities` + `detect`, with optional
  `setup`/`teardown` lifecycle hooks) that operates only on immutable
  `DatasetObject`s, is reference-free and deterministic, and never mutates
  benchmark state; an immutable `DetectorCapabilities` model (supported STO
  categories, modalities, logical types, required benchmark and ontology versions,
  optional and experimental capabilities) with pre-execution capability
  negotiation. Registration and entry-point discovery (`synthaudit_bench.detectors`
  group) return immutable `DetectorRegistry` values with lazy, isolation-safe
  loading (a broken plugin is recorded and skipped). `run_detector` is the isolated
  task boundary: it validates capabilities, honors the below-minimum rule, enforces
  an optional timeout, verifies the dataset was not mutated, and normalizes
  findings, turning every failure (capability, timeout `resource`, `runtime`,
  `invalid_findings`) into a structured `ErrorRecord` so one detector's failure
  never terminates a batch. The normalization pipeline resolves native identifiers
  to STO classes (exact/alias/deprecated/unknown-to-`STO-X00`), canonicalizes
  support, infers dispositions (Section 4.3), normalizes confidence and severity,
  collapses duplicates, orders deterministically, and validates every tuple against
  the normative tuple schema. Public API: `register_detector`, `discover_detectors`,
  `validate_detector`, `run_detector`, `normalize_findings`, `map_to_ontology`,
  `normalize_confidence`, `detector_capabilities`, `detector_metadata`. The core
  imports no specific detector; the reference adapter is an optional extra using
  this same protocol. Detector-protocol documentation with a minimal-plugin example
  and a fully tested (100% coverage) subsystem.
- WP7 Data acquisition and dataset loading: the `acquire` and `load` modules, the
  benchmark's ingestion layer. `acquire` is the only network-capable component and
  ships no network code: scripted fetching runs solely through an injected
  `Fetcher` (`(url) -> bytes`), and with none it is a pure local-cache-and-verify
  operation. It manages a deterministic content-addressed cache, enforces the
  license gate (non-scriptable licenses yield `FetchStub`s per Section 6.1.4),
  and fails closed on any SHA-256 mismatch (a bad fetch is deleted, a rotted cache
  entry is never returned verified). `load` reads the canonical CSV form (Section
  6.1.3) faithfully into an immutable `DatasetObject`, so its content hash equals
  the manifest instance identity; loads the companion split `T'` when `test_split`
  is set; and exposes analysis-only utilities that never mutate the identity-bearing
  table: automatic logical-type inference (Appendix D.5), missing-marker
  normalization (Section 5.2 N2), and below-minimum detection. `verify_dataset` is
  the comprehensive fail-closed ingestion gate (schema, per-file checksums,
  canonical parse, target existence, companion validity, and content identity).
  Public API: `acquire_dataset`, `fetch_stub`, `verify_source_checksums`,
  `cache_path`, `load_dataset`, `build_dataset_object`, `load_companion_split`,
  `verify_dataset`, `infer_column_types`, `normalize_missing_values`,
  `below_minimum`. Loading is reference-free, detector-independent, and performs no
  external access. Acquisition-and-loading documentation and a fully tested (100%
  coverage) subsystem.
- WP6 Registry and corpus management: the metadata-only `registry` subsystem
  (architecture `registry` module). A deterministic, cached loader over
  `registry/<corpus>/<id>.yaml` records that schema-validates each record, parses
  it into a `DatasetRecord`, and assigns its corpus (census, evaluation,
  controlled, conformance), evaluation split (public-dev, held-out), and content
  hash; an immutable indexed `Registry` with lookup by id, corpus, split,
  generator, domain, version, and hash; deterministic enumeration and filtering
  across every metadata axis; and referential-integrity checking (unique ids,
  corpus-versus-stratum consistency, split assignment, duplicate content hashes,
  and schema/ontology version compatibility). Public API: `load_registry`,
  `build_registry`, `validate_registry`, `referential_integrity`, `list_datasets`,
  `get_dataset`, `filter_registry`, `registry_index`, `enumerate_corpus`. No data
  downloading, CSV loading, or detector execution. Illustrative registry records
  across the four corpora, registry documentation, and a fully tested (100%
  coverage) subsystem.
- WP5 Configuration system: the layered configuration subsystem (architecture
  Section 8). Resolves the full precedence chain (packaged defaults <
  `configs/default.yaml` < profile < environment `SAB_*` < CLI < per-dataset
  overrides) with deep merging, complete per-value provenance, immutable version
  pins (with recorded, flag-gated override events), pinned per-STO-version
  detector thresholds shipped as package data, fail-closed schema validation, and
  a reproducible configuration hash. Public API: `load_config`, `resolve_config`,
  `config_hash`, `configuration_layers`, `load_profile`, `load_thresholds`,
  `effective_configuration`. Thresholds are detector defaults that change the
  configuration hash but never the benchmark semantics or gold labels; resolution
  never depends on file-discovery order. Configuration documentation and a fully
  tested (100% coverage) subsystem. The WP0 `configs/default.yaml` placeholder was
  updated to the normative config-schema shape (a bug fix required for WP5).
- WP4 Canonical serialization and content addressing: the foundational
  `canonical` module. Deterministic canonical JSON (UTF-8, sorted keys, compact
  separators, non-ASCII preserved, no BOM, NaN/Infinity rejected) and canonical
  RFC 4180 CSV (UTF-8, header row, `\n` line endings, comma delimiter, no BOM,
  specification Section 6.1.3); stable shortest-round-trip float formatting;
  deterministic collection ordering (sets sorted, dictionary insertion order
  never observed); lowercase-hex SHA-256 content addressing; and constant-time
  hash and byte integrity verification. Public API: `canonical_json`,
  `canonical_csv`, `format_float`, `canonicalize`, `sha256_bytes`,
  `content_hash`, `verify_hash`, `verify_bytes`. Output is byte-identical across
  operating systems and Python builds and reproduces the domain layer's identity
  model exactly (every object's `content_hash()` equals the SHA-256 of its
  canonical bytes). Canonicalization documentation and a fully tested (100%
  coverage) module with frozen regression vectors.
- WP3 Schema system: the validation boundary (architecture `schemas` module). The
  eight normative Draft 2020-12 JSON Schemas (artifact tuple, gold tuple, dataset
  record, report card, run manifest, metrics table, configuration, and the STO
  register schema) shipped as package data; an immutable, cached schema registry
  with deterministic loading, cross-schema `$ref` resolution, additive-minor
  version resolution and compatibility checks, and schema discovery; a stable
  public API (`load_schema`, `validate_instance`, `get_schema`, `list_schemas`,
  `schema_version`, `supported_versions`); and structured validation errors
  carrying the schema id, JSON pointer, offending value, and explanation.
  Validation never mutates its input; every domain object's serialization
  validates against its schema. The WP1 low-level primitives (`validate`,
  `check_schema`) are preserved unchanged as the layer this builds on.
  Schema-system documentation and a fully tested (100% coverage) schema layer.
- WP2 Domain model: the immutable domain layer (architecture Section 4) — the
  dataset metadata record, artifact and gold tuples, the loaded dataset object,
  the per-dataset audit result, the standardized report card, the run manifest,
  the scoring metrics table, the declarative figure specification, and the
  resolved configuration, together with their embedded value objects and metadata
  enums. Every object is a frozen, immutable dataclass with deterministic
  canonical serialization and content-addressed SHA-256 identity; objects that
  carry volatile run metadata (audit-result timing, report-card provenance,
  manifest timestamps) exclude it from identity so equal content hashes
  identically. The layer performs no IO, schema validation, scoring, or detector
  logic and never imports the reference implementation. Domain-model documentation
  and a fully tested (100% coverage) domain layer.
- WP1 Structural Trustworthiness Ontology (STO) v1.0: the normative class register
  (16 classes across groups A/S/R/P) and its Draft 2020-12 schema, shipped as
  package data; the immutable ontology domain model; a semantic-version value
  object with additive-minor compatibility; a deterministic, cached ontology
  loader with lookup, versioning, and deprecation APIs; structural-consistency
  validation; a generic JSON Schema validation helper; and the STO-to-SynthAudit
  traceability map with a completeness guard. Ontology documentation and a fully
  tested (100% coverage) ontology layer.
- WP0 project initialization: repository scaffold, packaging (`pyproject.toml`),
  the `synthaudit_bench` package skeleton, community files, the CI skeleton
  (lint, format, type, import contracts, tests, schema validation), the
  development `Makefile`, the documentation site skeleton, and the layered
  directory structure for the ontology, schemas, registry, corpus, and
  conformance suite.
- Import contract enforcing that the core library never imports the SynthAudit
  reference implementation.
- Pinned reference instrument (`synthaudit==0.1.0`) with a `uv.lock` lockfile and
  committed self-test provenance (11/11 planted, recall 1.0, negative-control
  1.0).
- Frozen pre-registration `PROTOCOL.md` v1.0 (tag `protocol-v1.0`) with the
  red-team fatal fixes and novelty positioning folded in.
- Benchmark identity: `CITATION.cff`, the two-version policy, and the Zenodo DOI
  reservation process (`docs/identity.md`).

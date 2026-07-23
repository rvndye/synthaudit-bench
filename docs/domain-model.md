# Domain model

The `synthaudit_bench.model` package is the pure domain layer of the benchmark
software (architecture Section 4). It is a set of frozen, immutable dataclasses
with deterministic serialization and content-addressed identity. The layer holds
no IO, no schema validation, no scoring, and no detector logic, and it never
imports the SynthAudit reference implementation; those concerns live in higher
layers and are added by later work packages. Everything here is a value: given
the same inputs it serializes to the same bytes and hashes to the same digest on
any machine, which is what makes runs of the benchmark reproducible and its
results comparable.

## The serialization interface

Every domain object exposes, where applicable, the same four-method interface.

`from_mapping(data)` reconstructs the object from a primitive mapping (the kind
produced by parsing JSON or YAML). It is total on schema-valid input: validation
happens at the boundary in a higher layer, so `from_mapping` assumes its input is
already valid and does not raise schema errors. `to_mapping()` returns the full
primitive mapping for the object, including any volatile run metadata.
`to_canonical()` returns the canonical byte serialization used for identity.
`content_hash()` returns the SHA-256 hex digest of those canonical bytes.

Identity-bearing aggregates (for example `DatasetRecord`, `AuditResult`,
`ReportCard`, `RunManifest`, `MetricsTable`, `FigureSpec`, `Config`) expose all
four methods. Embedded value objects that have no independent identity (for
example `License`, `Source`, `DetectorInfo`, `Pillars`, `Environment`, `Score`)
are serialization components and expose only `from_mapping` and `to_mapping`;
they are hashed transitively as part of the aggregate that contains them.

## Hashing model

Identity is content-addressed: an object's `content_hash()` is the SHA-256 of its
`to_canonical()` bytes, and two objects with equal content therefore hash
identically regardless of construction order or provenance.

For every object except `DatasetObject`, canonical bytes are deterministic UTF-8
JSON: keys sorted recursively, no insignificant whitespace, non-ASCII preserved,
and non-finite floats rejected. Because keys are sorted at serialization time,
the order in which mappings, class breakdowns, or dependency lists are supplied
never affects the hash. Collections that are logically sets or that have a
canonical order (a report card's artifact tuples, an audit result's tuples, a
manifest's per-dataset entries, a metrics table's per-dataset rows) are
normalized to sorted order in `__post_init__`, so equal content always produces
byte-identical output.

`DatasetObject` is the one object whose identity is defined over tabular data
rather than a JSON mapping. Its canonical form is the canonical CSV serialization
of its table (UTF-8, header row, `\n` line endings, RFC 4180 quoting, no
byte-order mark), matching the corpus content-hash definition (spec Section
6.1.3). It carries a live pandas DataFrame, so it cannot round-trip through a
primitive mapping; `from_mapping` is not applicable, `to_mapping()` returns a
descriptive summary (shape, columns, content hash) rather than the data, and
equality is defined element-wise over its content rather than by the default
dataclass comparison.

## Identity versus run metadata

Some objects carry volatile metadata that describes *a particular run* rather
than *the content that run produced*. Including such fields in the hash would make
identical results hash differently merely because they were produced at different
times, defeating the cache and the reproducibility contract. These objects
therefore compute identity over an internal `_identity_mapping()` that omits the
volatile fields, while `to_mapping()` still emits the full content so nothing is
lost on serialization.

Three objects apply this pattern. `AuditResult` excludes its `runtime_s` timing,
so the same findings hash identically whether the detector ran fast or slow.
`ReportCard` excludes its `provenance` block (run timestamp, seed, config hash),
so equal audit content hashes identically across runs. `RunManifest` excludes its
injected `timestamps`, so two runs that produced identical results and identical
provenance hash identically regardless of when they ran. In each case the excluded
data remains present in `to_mapping()` and is persisted; it simply does not
participate in identity.

## Object lifecycle

A domain object is **created** from validated input (a mapping via `from_mapping`,
or direct construction by a pure transform), **consumed** by other pure transforms
that read it and return new objects, and **persisted** only as generated artifacts
under `results/`. It is never mutated in place: transforms produce new values
rather than modifying existing ones. Validation is not part of this layer; a
mapping is validated against its JSON Schema at the boundary before `from_mapping`
is called, and this layer trusts that contract.

## Immutability guarantees

Every domain object is a `@dataclass(frozen=True, slots=True)` (or, for
`DatasetObject`, `frozen=True` with content-based equality). Frozen dataclasses
forbid attribute rebinding after construction, and `slots=True` forbids adding new
attributes, so instances cannot be changed once built. Scalar and tuple fields are
immutable by construction; mapping-typed fields (a loader's options, a set of
per-file checksums, an environment's dependency versions, a configuration's
thresholds) are held as `types.MappingProxyType` read-only views so the contents
cannot be mutated through the object.

The only writes any object performs on itself happen inside `__post_init__`, which
uses `object.__setattr__` — the sanctioned escape hatch for frozen dataclasses —
solely to normalize collections into canonical sorted order at construction time.
After `__post_init__` returns, the object is fully immutable. No domain object
reads a clock, consults a random source, touches the filesystem or network, or
mutates any global state; all such effects are pushed to higher layers, which
keeps the domain layer deterministic and trivially testable.

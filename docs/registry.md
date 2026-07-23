# Registry and corpus management

The `synthaudit_bench.registry` package is the metadata backbone of the corpus.
It loads the declarative dataset records, organizes them by corpus and split,
validates their referential integrity, and answers enumeration, lookup, and
filtering queries deterministically. It is metadata-only: it reads registry files
and never downloads data, loads tables, or runs detectors. Data acquisition, CSV
loading, and detection are the responsibility of later subsystems.

## Registry lifecycle

A registry is loaded from a root directory of declarative records, validated, and
returned as an immutable, indexed value. `load_registry` discovers every
`<root>/<corpus>/<id>.yaml` record in deterministic order, validates each against
the normative dataset schema, parses it into a `DatasetRecord` (which enforces the
enum vocabularies for frame stratum, generator family, provenance confidence, and
task), assigns its corpus, split, and content hash, rejects duplicate identifiers
and split or manifest entries that reference unknown datasets, and builds the
index. `build_registry` does the same from records already in memory, which is
what makes the subsystem testable without a filesystem. `validate_registry` loads
(if given a path) and runs the full referential-integrity check, raising on any
violation. Path-based loads are cached, so repeated loads of the same registry
return the same object. Loading reads only registry files and never depends on
filesystem ordering; every result is sorted deterministically.

## Corpus architecture

The registry spans four corpora. The Census Corpus is the characterization frame
of public synthetic and simulated datasets; its records carry the `census` frame
stratum and are not scored. The Evaluation Corpus is the scored benchmark, drawn
from the `planted`, `controlled`, and `adjudicated_real` strata and partitioned
into splits. The Controlled corpus holds the controlled-generation study outputs
(`controlled` stratum). The Conformance corpus holds the compliance-suite
fixtures. Each corpus is a subdirectory of the registry root, and a record's
corpus is its directory; the record's frame stratum must be consistent with its
corpus, which the integrity check enforces.

## Metadata model

Each record is one dataset's metadata: a stable kebab-case identifier, a frame
stratum, a domain, a generator family and optional tool and version, a provenance
confidence, the task and target, the license and redistribution flags, the source
URLs and retrieval hashes, a declarative loader spec, transparency disclosures,
and a citation. A registry entry pairs that record with its corpus, its optional
evaluation split, and its optional canonical content hash. The content hash is the
instance identity from the release manifest; because the registry is metadata-only
it is present only when a manifest is supplied, which is why hash-based indexing
and duplicate-hash detection are available only when a manifest is present.

## Corpus partitioning

The Evaluation Corpus is partitioned into a `public-dev` split, whose gold labels
are released, and a `held-out` split, whose gold is withheld. Split assignment
comes from a splits file (grouping dataset identifiers under each split, or mapping
each identifier to its split) and is fixed within a benchmark version. The
integrity check requires that every evaluation dataset is assigned exactly one
split and that no non-evaluation dataset is assigned a split; a splits file that
references an unknown dataset is rejected at load.

## Lookup model

The registry precomputes a deterministic index: a map from identifier to entry,
and maps from corpus, split, generator family, domain, generator version, and
content hash to the sorted identifiers that carry them. `get_dataset` resolves an
identifier to its entry and raises `UnknownDatasetError` on a miss; `registry_index`
returns the whole index; and `enumerate_corpus` returns a corpus in identifier
order. Index construction is reproducible: the same records always yield the same
index regardless of the order they were read.

## Filtering

Enumeration and filtering both return entries sorted by identifier. Enumeration
covers each metadata axis: all datasets, by corpus, by split, by generator family,
by domain, by task, by modality, by license, by transparency flags, and by
provenance confidence. `filter_registry` combines any of these criteria in one
query and returns the datasets that match all of them, and `Registry.filter`
accepts an arbitrary predicate for anything the built-in axes do not cover. Every
result is deterministic.

## Integrity guarantees

`referential_integrity` returns a deterministic report of every violation without
raising, and `validate_registry` raises on the first failing registry. The checks
are: schema validity and unique identifiers (enforced at load), corpus-versus-
stratum consistency (census records are the census stratum, evaluation records are
one of the evaluation strata, and so on), split assignment (every evaluation
dataset has a split and no other dataset does), duplicate content hashes when
hashes are available, and optional schema and ontology version compatibility
against the installed schema set and the available ontology versions. A registry
that passes every rule is safe for the downstream stages to consume.

## Examples

```python
from synthaudit_bench import registry

reg = registry.load_registry("registry")                       # load and index
registry.validate_registry(reg, sto_version="1.0.0", schema_version="1.0.0")

registry.enumerate_corpus(reg, "census")                       # the census frame
reg.by_split("public-dev")                                     # released evaluation split
reg.by_generator_family("gan")                                 # by generator family
registry.filter_registry(reg, corpus="evaluation", domain="finance")

entry = registry.get_dataset(reg, "controlled-ctgan-adult")
entry.corpus, entry.split                                      # Corpus.EVALUATION, Split.HELD_OUT

report = registry.referential_integrity(reg)
report.ok                                                      # True when the registry is sound
```

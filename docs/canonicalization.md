# Canonicalization and content addressing

The `synthaudit_bench.canonical` module is the foundation the whole benchmark
stands on. It defines the one deterministic byte representation of every
artifact and the SHA-256 identity derived from it. Reproducibility, caching, and
cross-implementation comparison all reduce to a single promise this module
keeps: equal semantic content produces equal bytes, and equal bytes produce
equal hashes, on any machine.

## Canonicalization philosophy

A value can be written many ways. A JSON object can order its keys freely, escape
non-ASCII or not, and pad numbers; a CSV file can use any newline, quoting style,
or byte-order mark. Any of that variation would make two copies of the same
content hash differently, which would break every downstream guarantee. The
canonical form removes the freedom: it fixes exactly one spelling for each value,
chosen to be stable across operating systems, Python builds, and processes, and
independent of anything nondeterministic such as dictionary insertion order, a
clock, a random source, or a memory address.

Structured data has a canonical JSON form: UTF-8 encoded, keys sorted at every
level, compact separators with no insignificant whitespace, non-ASCII preserved
rather than escaped, no byte-order mark, and NaN or Infinity rejected outright
because they have no canonical JSON form. Tabular data has a canonical CSV form
(specification Section 6.1.3): UTF-8, a header row, `\n` line endings only, a
comma delimiter, minimal RFC 4180 quoting, and no byte-order mark. Every function
is pure and returns immutable `bytes` or `str`, never mutating its input and
never reading hidden state, which is what makes the output byte-identical
everywhere.

## The public API

`canonicalize(obj)` returns a canonical, JSON-primitive normal form of a value:
mappings become dictionaries with string keys, sets and frozensets become lists
sorted into a deterministic order, other sequences keep their order, and scalars
pass through. `canonical_json(obj)` returns the canonical JSON bytes, and
`canonical_csv(table)` returns the canonical CSV bytes of a table.
`format_float(x)` returns the canonical decimal string for a finite float, the
shortest string that round-trips to the same double, which is what the JSON
encoder also uses.

`sha256_bytes(data)` returns the lowercase-hex SHA-256 of raw bytes.
`content_hash(obj)` is the content address of a structured object: the SHA-256 of
its canonical JSON. `verify_hash(obj, expected)` and `verify_bytes(data,
expected)` check an object or a raw byte artifact against an expected hash with a
constant-time, case-insensitive comparison, for integrity checking of cached
results and downloaded corpus files.

## Content-addressing model

An object's identity is the hash of its canonical bytes. Because the bytes are
canonical, identity depends only on semantic content: two objects that mean the
same thing are byte-identical and therefore hash-identical, and any change in
meaning changes the bytes and so the hash. Hashes are SHA-256 in lowercase
hexadecimal, computed over canonical serialized bytes and nothing else. No
timestamp, memory address, object id, or other nondeterministic metadata ever
enters a hash.

The domain layer builds directly on this. Each domain object serializes to a
canonical form and takes its `content_hash()` as the SHA-256 of those bytes, so
`sha256_bytes(obj.to_canonical())` always equals `obj.content_hash()`. For a
loaded dataset the canonical form is its canonical CSV, matching the corpus
content-hash definition, so a dataset's identity is exactly
`sha256_bytes(canonical_csv(table))`. Objects that carry volatile run metadata
(an audit result's timing, a report card's provenance, a run manifest's
timestamps) exclude that metadata from their canonical bytes, so equal findings
hash identically no matter when or how fast they were produced, while the full
content is still serialized for storage.

## Identity, serialization, and reproducibility guarantees

The guarantees follow from the canonical form. Equivalent objects always hash
identically: a dictionary written in one key order and the same dictionary
written in another produce the same bytes and the same hash, and a set written as
`{3, 1, 2}` canonicalizes to `[1, 2, 3]` just as a list `[1, 2, 3]` does.
Non-equivalent canonical objects always produce different hashes, and order is
treated as semantic for sequences, so `[1, 2]` and `[2, 1]` differ.

Serialization is deterministic and platform-independent: sorted keys remove
insertion-order dependence, UTF-8 with no byte-order mark removes encoding
variation, `\n`-only line endings remove newline variation, and the shortest
round-trip float format removes numeric-formatting variation. None of these read
the operating system or locale, so canonical output generated on different
systems is byte-identical. Reproducibility is the consequence: rerunning a
computation, restarting the process, or moving to another machine yields the same
canonical bytes and therefore the same content address, which is what lets the
cache treat a content hash as a stable key and lets a run be checked for
byte-exact reproduction.

## Examples

Equivalent objects hash identically regardless of key order or set spelling:

```python
from synthaudit_bench import canonical

canonical.canonical_json({"b": 1, "a": 2})        # b'{"a":2,"b":1}'
canonical.content_hash({"a": 1, "b": 2}) == canonical.content_hash({"b": 2, "a": 1})   # True
canonical.content_hash({"s": [1, 2, 3]}) == canonical.content_hash({"s": {3, 2, 1}})   # True
```

Content addressing and integrity verification:

```python
digest = canonical.content_hash({"dataset_id": "grid", "artifacts": []})
canonical.verify_hash({"dataset_id": "grid", "artifacts": []}, digest)   # True

raw = canonical.canonical_csv(table)
canonical.verify_bytes(raw, canonical.sha256_bytes(raw))                 # True
```

A dataset's identity is the SHA-256 of its canonical CSV, and it is stable across
runs and machines:

```python
canonical.sha256_bytes(canonical.canonical_csv(table))   # the dataset content hash
```

# Schema system

The `synthaudit_bench.schemas` package is the validation boundary of the
benchmark software. It owns the normative Draft 2020-12 JSON Schemas that define
the on-the-wire shape of every artifact, loads them into an immutable cached
registry, resolves versions and cross-schema references, and validates instances
into structured, actionable errors. The domain layer deliberately does no
validation: its `from_mapping` constructors assume already-valid input, and this
package is what makes that assumption safe by validating at the point where data
enters the system.

## Schema architecture

Every normative schema ships as package data so an installed wheel can validate
without any external files. Seven schemas live in the `schema_data` package:
`artifact-tuple`, `gold-tuple`, `dataset`, `report-card`, `run-manifest`,
`metrics`, and `config`. An eighth, `ontology`, is the schema for the STO
register; its canonical home is the `sto_data` package from the ontology work,
and the registry serves it from there so it is reachable through the same API as
the rest. Each schema declares a `$schema` (Draft 2020-12), a stable `$id` of the
form `https://synthaudit-bench.org/schemas/v1.0/<name>.json`, and a `version`.

Schemas reference one another rather than duplicating shared shapes. A report
card's `artifacts` entries reference the artifact-tuple schema by a relative
`$ref` resolved against the `$id` base. The registry builds a reference set from
every schema keyed by its `$id`, so these cross-schema references resolve without
network access and without inlining.

The public API is small and independent of the implementation. `load_schema`
returns an immutable schema handle, `get_schema` returns a fresh copy of the
schema document, `validate_instance` validates a mapping against a named schema,
`list_schemas` enumerates the registered names, and `schema_version` and
`supported_versions` report versions. The low-level primitives `validate`
(validate against an explicit schema mapping) and `check_schema` (check that a
document is a well-formed schema) are retained unchanged from the ontology work
and are the layer the named-schema API is built on.

## Loading process

Loading is deterministic. The registry discovers the packaged schema files in
sorted order, reads each one, and checks that it is a valid Draft 2020-12 schema
as it is registered; a malformed schema document raises `InvalidSchemaError`
immediately rather than failing later at validation time. Each document is stored
as an immutable schema handle carrying its name, parsed version, `$id`, and a
canonical (sorted-key) serialization of the document. Because loading reads the
same bytes and canonicalizes the same way every time, two registries built from
the same package data are byte-for-byte identical.

Reading the same package data on every construction and canonicalizing keys makes
the loaded schemas reproducible across machines and processes. The version of a
schema is taken from its `version` key when present, and otherwise derived from
the `vMAJOR.MINOR` segment of its `$id`, so the ontology schema (which predates
the `version` convention) still reports a coherent version.

## Validation lifecycle

Validation of an instance proceeds in three steps: resolve the named schema to a
concrete version, obtain that schema's compiled validator, and iterate the
validator's errors deterministically. Errors are ordered by JSON pointer and then
message, and the first is reported, so the same invalid input always yields the
same error. The instance is never mutated: validation only reads it.

The relationship to the domain layer is a contract. Every domain object's
`to_mapping()` output validates against that object's schema, and every mapping
that validates can be reconstructed by the object's `from_mapping()`. Validation
happens at the boundary (when reading a registry record, a gold file, or a
persisted result), and the pure domain transforms downstream then trust the data.

## Caching

Two layers of caching keep validation cheap without introducing mutable global
state. The process-wide registry of packaged schemas is built once and memoized;
because it is a pure function of immutable package data, the memoization is a
cache rather than shared mutable state. Within a registry, the compiled validator
for each resolved schema is built on first use and reused thereafter, so
repeated validation against the same schema does not recompile it. The immutable
schema handles hand out fresh copies of their document on every `as_dict` call,
so a caller can never mutate the cached schema through a returned value.

## Version compatibility

Schema versions follow the same additive-minor rule as the rest of the benchmark:
a registered version satisfies a requested version when they share a major version
and the registered version is at least the requested one. Requesting a schema
without a version returns the latest registered version; requesting a specific
version returns the highest registered version that satisfies it, so a consumer
pinned to `1.0.0` transparently receives a backward-compatible `1.2.0` if that is
what is installed. A request whose major version is not available, or whose minor
version exceeds every registered version, raises `SchemaCompatibilityError`, and
`is_compatible` answers the same question without raising. Today every schema is
at `1.0.0`; the machinery exists so that future minor revisions resolve correctly
without consumer changes.

## Error reporting

Validation failures raise `SchemaValidationError`, which carries the structured
location of the failure rather than only a message: the schema identifier that
was violated, a JSON pointer to the offending location, the offending value at
that location, and the human-readable explanation from the validator. A bad
enumeration value deep inside a report card, for example, reports the pointer
`/artifacts/0/class` and the value that failed, so the caller can point directly
at the problem. Unknown schema names raise `UnknownSchemaError`, incompatible
version requests raise `SchemaCompatibilityError`, and malformed schema documents
raise `InvalidSchemaError`. All of these extend the benchmark's `SchemaError`, so
a caller can catch the whole category or discriminate among the specific causes.

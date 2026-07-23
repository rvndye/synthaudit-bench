# Normative JSON Schemas (package data)

These are the normative Draft 2020-12 JSON Schemas that define the on-the-wire
shape of every SynthAudit-Bench artifact. They ship as package data and are
loaded by the schema subsystem (`synthaudit_bench.schemas`) into an immutable,
cached registry; instances are validated against them at every IO boundary.

Each schema declares a `$schema` (Draft 2020-12), a stable `$id`
(`https://synthaudit-bench.org/schemas/v1.0/<name>.json`), and a `version`.
Cross-schema references (for example a report card's `artifacts` referencing the
artifact tuple) are expressed as relative `$ref`s against the `$id` base and are
resolved by the registry.

| Schema file | Registered name | Purpose | Specification |
|---|---|---|---|
| `artifact-tuple.schema.json` | `artifact-tuple` | One predicted artifact tuple | Section 5.3, Appendix A |
| `gold-tuple.schema.json` | `gold-tuple` | One ground-truth gold tuple | Section 5.4, Appendix A |
| `dataset.schema.json` | `dataset` | Dataset metadata record | Section 7, Appendix B |
| `report-card.schema.json` | `report-card` | Standardized report card | Section 8, Appendix C |
| `run-manifest.schema.json` | `run-manifest` | Reproducibility run manifest | Section 9.6, 9.7 |
| `metrics.schema.json` | `metrics` | Scored metrics table | Section 5.6 |
| `config.schema.json` | `config` | Resolved run configuration | Architecture Section 8 |

The ontology (STO register) schema is registered under the name `ontology`; its
canonical home is the `sto_data/` package (WP1), and the registry serves it from
there so it is discoverable through the same API.

Date-typed fields carry a `format: "date"` annotation. Formats are validated as
annotations only (not assertions), so validation is deterministic and identical
across environments regardless of which optional format libraries are installed.

# schemas/

The normative JSON Schemas (Draft 2020-12) that define every machine-readable
artifact in the benchmark:

- `artifact-tuple.schema.json`, `gold-tuple.schema.json`
- `dataset.schema.json` (the metadata record)
- `report-card.schema.json`
- `run-manifest.schema.json`, `metrics.schema.json`, `config.schema.json`

Every artifact crossing an IO boundary is validated against its schema. Each
schema ships with valid and invalid fixtures under `tests/schema/`. Schemas are
populated in the metadata-schema work package.

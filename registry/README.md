# registry/

The benchmark registry: one declarative metadata record per dataset, validated
against `schemas/dataset.schema.json`. Records are data, not code; the loader is
generic.

- `census/<id>.yaml` — Census Corpus records (characterization frame).
- `evaluation/<id>.yaml` — Evaluation Corpus records (scored, labeled).

Each record carries a stable `id`, `frame_stratum`, `domain`, `generator_family`,
`provenance_confidence`, `target`, `license`, `source` (with checksums), a
declarative `loader` spec, and `transparency` disclosures. Populated in the
registry work package.

# registry/

The benchmark registry: one declarative metadata record per dataset, validated
against the normative `dataset` schema. Records are data, not code; the loader in
`synthaudit_bench.registry` is generic and metadata-only (it never downloads
data, loads tables, or runs detectors).

Layout: one `<id>.yaml` record per dataset under a per-corpus subdirectory.

- `census/<id>.yaml` — Census Corpus records (characterization frame; `frame_stratum: census`).
- `evaluation/<id>.yaml` — Evaluation Corpus records (scored, labeled; `planted`, `controlled`, or `adjudicated_real` strata).
- `evaluation/splits.json` — the public-dev vs held-out split assignment (Section 6.3.3).
- `controlled/<id>.yaml` — Controlled-generation study records (`frame_stratum: controlled`).
- `conformance/<id>.yaml` — Compliance-suite fixtures (`planted` or `controlled`).

Each record carries a stable `id`, `frame_stratum`, `domain`, `generator_family`,
`provenance_confidence`, `target`, `license`, `source` (with checksums), a
declarative `loader` spec, and `transparency` disclosures. The registry is loaded,
indexed, and validated for referential integrity (schema validity, unique ids,
corpus-versus-stratum consistency, split assignment, and duplicate content hashes
when a manifest is present).

The records currently committed here are **illustrative scaffolding** so the
registry subsystem is loadable and documented; the census and evaluation work
packages replace them with the real corpus records and their content hashes.

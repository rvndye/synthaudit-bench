# corpus/

Dataset data (or fetch stubs) for the two corpora.

- `census/<id>/` — natural datasets for characterization.
- `evaluation/<id>/` — labeled, balanced datasets for scoring.
- `evaluation/gold/<id>.json` — public-dev ground-truth tuples (held-out gold is
  withheld from the public release).
- `evaluation/splits.json` — public-dev vs held-out assignment.

Data files here are git-ignored; datasets are tracked by content hash in the
release manifest and, where a license forbids redistribution, by a fetch stub in
the registry. Canonical serialization is UTF-8 CSV (RFC 4180). Populated across
the acquisition, census, and evaluation work packages.

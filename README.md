# SynthAudit-Bench

**A reference-free structural trustworthiness benchmark for synthetic and simulated tabular datasets.**

SynthAudit-Bench measures how well an auditing system recovers, from a released
tabular file alone (no access to the real source data and no access to the
generator), the structural artifacts that can invalidate that file as a machine
learning benchmark: exact column identities, rule- and threshold-derived labels,
functional dependencies, duplication, sampling signatures, ordering and
cross-split leakage, and predictive shortcuts.

This repository is the **benchmark** (the ontology, corpora, schemas, task, and
compliance suite) together with a small Python library that runs it. The
benchmark is defined by the frozen specification, not by any one tool. The core
library is **detector-agnostic**: it never imports the SynthAudit reference
implementation, and any conforming detector can be plugged in.

> SynthAudit-Bench (this benchmark) is distinct from SynthAudit (one reference
> implementation). See `GOVERNANCE.md` and `docs/identity.md`.

## Status

Pre-alpha. The repository is being implemented work package by work package
following the frozen Execution Manual. See `CHANGELOG.md`.

## Install (development)

```bash
git clone https://github.com/rvndye/synthaudit-bench.git
cd synthaudit-bench
python -m pip install -e ".[dev]"
make check          # lint, format, type, import contracts, tests
```

## Repository layout

Normative data and specifications live in `sto/`, `schemas/`, `registry/`,
`corpus/`, and `conformance/`; the library lives in `src/synthaudit_bench/`;
generated outputs land in `results/` and `figures/` (git-ignored). Every
directory carries a `README.md` explaining its purpose.

## Documentation

The frozen specification, ontology, and developer guide are published from
`docs/`. Start with `docs/index.md`.

## Citation

The benchmark is cited by name and version with its DOI (see `CITATION.cff`),
separately from the accompanying paper. See `GOVERNANCE.md` for the citation
policy.

## License

Apache-2.0 (`LICENSE`). Bundled datasets keep their original licenses.

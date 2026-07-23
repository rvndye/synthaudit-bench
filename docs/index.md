# SynthAudit-Bench

A reference-free structural trustworthiness benchmark for synthetic and simulated
tabular datasets.

SynthAudit-Bench measures how well an auditing system recovers, from a released
tabular file alone, the structural artifacts that can invalidate that file as a
machine learning benchmark. The benchmark is defined by its frozen specification
and is independent of any single tool: the core library is detector-agnostic and
never imports the SynthAudit reference implementation.

## Where to start

- **Governance and versioning:** see the repository `GOVERNANCE.md`.
- **Contributing:** see `CONTRIBUTING.md`.
- **Future work and scope boundaries:** see [Future work](future-work.md).

The specification, ontology, and API reference are published here as the
implementing work packages land.

!!! note
    This site is built with `mkdocs build`. The full specification pages and API
    reference are added by later work packages.

# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The **software**
package follows [Semantic Versioning](https://semver.org/); the **benchmark**
(corpus, ontology, specification) is versioned independently per `GOVERNANCE.md`.

## [Unreleased]

### Added
- WP1 Structural Trustworthiness Ontology (STO) v1.0: the normative class register
  (16 classes across groups A/S/R/P) and its Draft 2020-12 schema, shipped as
  package data; the immutable ontology domain model; a semantic-version value
  object with additive-minor compatibility; a deterministic, cached ontology
  loader with lookup, versioning, and deprecation APIs; structural-consistency
  validation; a generic JSON Schema validation helper; and the STO-to-SynthAudit
  traceability map with a completeness guard. Ontology documentation and a fully
  tested (100% coverage) ontology layer.
- WP0 project initialization: repository scaffold, packaging (`pyproject.toml`),
  the `synthaudit_bench` package skeleton, community files, the CI skeleton
  (lint, format, type, import contracts, tests, schema validation), the
  development `Makefile`, the documentation site skeleton, and the layered
  directory structure for the ontology, schemas, registry, corpus, and
  conformance suite.
- Import contract enforcing that the core library never imports the SynthAudit
  reference implementation.
- Pinned reference instrument (`synthaudit==0.1.0`) with a `uv.lock` lockfile and
  committed self-test provenance (11/11 planted, recall 1.0, negative-control
  1.0).
- Frozen pre-registration `PROTOCOL.md` v1.0 (tag `protocol-v1.0`) with the
  red-team fatal fixes and novelty positioning folded in.
- Benchmark identity: `CITATION.cff`, the two-version policy, and the Zenodo DOI
  reservation process (`docs/identity.md`).

# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The **software**
package follows [Semantic Versioning](https://semver.org/); the **benchmark**
(corpus, ontology, specification) is versioned independently per `GOVERNANCE.md`.

## [Unreleased]

### Added
- WP0 project initialization: repository scaffold, packaging (`pyproject.toml`),
  the `synthaudit_bench` package skeleton, community files, the CI skeleton
  (lint, format, type, import contracts, tests, schema validation), the
  development `Makefile`, the documentation site skeleton, and the layered
  directory structure for the ontology, schemas, registry, corpus, and
  conformance suite.
- Import contract enforcing that the core library never imports the SynthAudit
  reference implementation.

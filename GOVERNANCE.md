# Governance

This document is the operational summary of the governance clauses in the frozen
benchmark specification. Where this file and the specification differ, the
specification governs.

## Roles

- **Maintainers** steward the specification, ontology, corpora, schemas, and
  compliance suite, and cut releases.
- **Contributors** propose datasets, ontology classes, and corrections through
  the change process below.

## Two version lines

- **Software version** (`synthaudit_bench.__version__`, in `pyproject.toml`)
  tracks the Python package. It follows Semantic Versioning.
- **Benchmark version** (the corpus, ontology, and specification) is versioned
  independently, pinned in `configs/default.yaml`, and recorded in every release
  manifest and DOI. The current target benchmark version is `1.0.0`.

## Semantic versioning (benchmark)

- **MAJOR**: any change that can alter a conforming system's score or break
  prior gold or outputs (task, metrics, matching, removing or redefining an STO
  class, removing datasets, split reassignment).
- **MINOR**: backward-compatible additions (new datasets, new STO classes with
  new identifiers, new optional fields, added held-out instances).
- **PATCH**: corrections that do not change semantics.

Every release is immutable and DOI-stamped. Dataset instances are immutable
(content-hash identity); corrections create a new instance and tombstone the old.

## Ontology versioning

STO is versioned independently and pinned by each benchmark release. Class
identifiers are permanent; incompatible redefinition requires a new identifier
and deprecation of the old.

## Submissions

A dataset submission includes a schema-valid metadata record, license and
redistributability, source and checksums (or a fetch stub), and, for the
Evaluation Corpus, gold with evidence and (for adjudicated gold) the
two-adjudicator protocol and its agreement statistic.

## Change process

Changes are proposed in writing (issue or RFC) stating motivation, the exact
normative change, backward-compatibility impact, and the version bump. Proposals
are reviewed publicly; acceptance requires maintainer sign-off; the change lands
with its version bump and a `CHANGELOG.md` entry.

## Citation policy

The benchmark and the accompanying paper are cited separately. Users of a corpus
version cite the benchmark by name, version, and DOI (`CITATION.cff`). The
ontology may be cited independently. Citing the SynthAudit reference
implementation is not a citation of the benchmark, and vice versa.

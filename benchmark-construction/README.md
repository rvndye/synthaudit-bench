# SynthAudit-Bench Benchmark Construction Package (Phase 3)

This directory is the benchmark-construction package: the protocols, templates, and
gates for building the SynthAudit-Bench 1.0.0 benchmark artifact that the frozen
software evaluates. It creates no datasets, no gold, and no results.

## Documents (read in order)

1. `BENCHMARK-BLUEPRINT.md` — the master construction plan and the frozen invariants every other document obeys.
2. `CORPUS-PROTOCOL.md` — census and evaluation corpus construction, licensing, versioning, metadata, and the held-out split.
3. `ANNOTATION-MANUAL.md` — the gold annotation protocol for two independent annotators (definitions, decision rules, examples, edge cases, adjudication, QA).
4. `CONFORMANCE-PLAN.md` — the CS-1..CS-7 fixture organization, gold and expected-output policy, and tolerances.
5. `EVALUATION-PROTOCOL.md` — baselines, execution order, metrics, aggregation, reporting, and reproducibility.
6. `RELEASE-CHECKLIST.md` — versioning, release, update, deprecation, and governance policy, and the first-release checklist.

## Templates

`templates/` holds the fill-in artifacts, each schema-valid where a frozen schema applies:

- `dataset-record.template.yaml` — a registry record (validates against `dataset.schema.json`).
- `gold-objective.template.json`, `gold-adjudicated.template.json` — gold files (validate against `gold-tuple.schema.json`).
- `MANIFEST.template.json` — the release manifest (Section 6.1.5).
- `tolerances.template.json` — the conformance tolerances (v1.0 defaults).
- `controlled-vocabularies.md` — the frozen and corpus-fixed vocabularies.
- `census-decision-log.template.csv`, `annotation-record.template.csv` — workflow logs.

## Operational planning documents (in the content tree)

- `corpus/census/frame.md` — the census frame enumeration (to fix before collection).
- `corpus/census/inclusion-exclusion.md` — census inclusion and exclusion criteria and the decision log.
- `corpus/evaluation/design.md` — the evaluation corpus design targets.

## Boundaries

The SynthAudit-Bench software is frozen and immutable; nothing here modifies it.
This package plans benchmark content only. Executing the plan (enumerating the
census, generating the strata, annotating datasets, establishing gold, running
baselines) is the next phase and is deliberately out of scope: this package
annotates nothing, fabricates no gold, and runs no detectors.

# benchkit: SynthAudit-Bench construction infrastructure

`benchkit` is the **benchmark execution infrastructure** for SynthAudit-Bench. It is
the tooling humans run to construct the benchmark exactly as the published
construction package specifies. It is not the benchmark software and it is not
benchmark data.

## Separation of concerns

Three things are kept strictly separate, and this package is only the middle one:

| Layer | Location | Status |
|---|---|---|
| **software** | `src/synthaudit_bench/` | frozen v1.0.0; imported here, never modified |
| **infrastructure** | `tools/benchkit/` (this package) | the tooling |
| **data** | `corpus/`, `registry/`, `conformance/`, `evaluation/gold/` | produced by humans running this tooling; empty until later phases begin |

`benchkit` drives the frozen public API (`synthaudit_bench.acquire`, `.canonical`,
`.gold`, `.schemas`, `.registry`, `.release`, and the frozen `bench` CLI). It never
reimplements frozen behavior.

## Anti-fabrication guarantees

Every tool consumes real, human-provided inputs and fails closed when they are
absent. The tooling **never** fabricates datasets, annotations, gold, expected
outputs, or metrics; **never** simulates human annotation; and creates illustrative
records only inside clearly-marked unit-test fixtures (`tools/tests/_fixtures.py`).
On the empty benchmark it produces empty results or fails closed, by design.

## Engineering properties

Deterministic (no wall-clock; seeded via the frozen `derive_seed`), reproducible
(canonical JSON serialization; `packaging.verify_reproducible`), idempotent (identical
inputs yield byte-identical outputs), schema-validated (frozen `schemas` and
`gold`/`registry` validators), and modular (one module per deliverable).

## Install and run

```bash
# from the repository root, with the frozen software installed
pip install -e .            # the frozen synthaudit-bench
pip install -e tools        # this infrastructure package (provides the `benchkit` CLI)
python -m benchkit --version
```

## The nine pipelines and example invocations

Inputs below are files a human produces (query results, downloaded data, completed
annotation forms). None of them exist on the empty benchmark; the commands are the
interface, not a script to run now.

```bash
# 1. Census enumeration: candidate descriptors (JSONL) -> reproducible census records
python -m benchkit census enumerate --candidates candidates.jsonl --out census.jsonl

# 2. Acquisition: acquire a registry's records via the frozen acquisition (fail closed)
python -m benchkit acquire --registry registry --cache .cache --out acquire-report.json

# 3. Corpus builder: plan an evaluation corpus over the census pool (seeded, no content)
python -m benchkit corpus plan --census census.jsonl --out corpus-plan.json \
    --seed 42 --held-out-fraction 0.25 --balance-key generator_family

# 4. Annotation packets: generate blank forms + assignment manifests (no labels)
python -m benchkit annotation package --assignment assignment.json --out packets/

# 5. Annotation validation: validate completed annotations (fail closed)
python -m benchkit annotation validate --annotations annotations.jsonl --out validation.json

# 6. Agreement analysis: Cohen's kappa and disagreements between two annotators (no gold)
python -m benchkit agreement --a annotatorA.jsonl --b annotatorB.jsonl \
    --annotator-a A --annotator-b B --out agreement.json

# 7. Gold assembly: reconciled annotations -> gold files (consume only; never infer)
python -m benchkit gold assemble --annotations reconciled.jsonl --out evaluation/gold/

# 8. Packaging: validate a release structure (Section 6.1.6)
python -m benchkit package validate --registry registry --gold evaluation/gold \
    --splits evaluation/splits.json --out release-validation.json

# 9. Baseline runner: run the frozen bench CLI over a completed release (fail closed if empty)
python -m benchkit baseline run --csv data/*.csv --out-dir results --gold evaluation/gold \
    --split public-dev --report baseline-run.json
```

## Development

```bash
cd tools
ruff check . && ruff format --check .
mypy
python -m pytest
```

Tests use only clearly-marked synthetic fixtures and never write into the benchmark
data directories.

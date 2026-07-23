# Benchmark identity, naming, and versioning

SynthAudit-Bench is designed as a durable, independently-citable artifact. This
page fixes its identity so it can be referenced and versioned for the long term.

## Name

**SynthAudit-Bench** is the benchmark: the Structural Trustworthiness Ontology
(STO), the census and evaluation corpora, the tool-agnostic auditing task with
baselines, the report-card schema, and the compliance suite.

**SynthAudit** is a separate reference implementation (one detector). Citing one
is not citing the other (see `GOVERNANCE.md`, citation policy).

## Two version lines

- **Software version** — `synthaudit_bench.__version__` in `pyproject.toml`.
  Tracks the Python package; follows Semantic Versioning. Currently `0.0.1`
  (pre-release).
- **Benchmark version** — the corpus, ontology, and specification. Versioned
  independently, pinned in `configs/default.yaml` (`benchmark_version`), and
  recorded in every release manifest and DOI. Target: `1.0.0`.

The Semantic-Versioning rules for the benchmark (what counts as MAJOR, MINOR, and
PATCH) are in `GOVERNANCE.md`.

## DOI reservation

Each benchmark release is archived on Zenodo and receives a version DOI; a
concept DOI (resolving to the latest version) is reserved on the first deposit.
The DOI is added to `CITATION.cff` and recorded in the release manifest at the
release work package. Until then, `CITATION.cff` intentionally omits the DOI
field so it remains valid.

To reserve and mint the DOI at release time:

1. Create a Zenodo deposition for the repository (concept record).
2. Record the reserved concept DOI here and in `CITATION.cff`.
3. On each tagged benchmark release, publish the version and record its version
   DOI in the release manifest.

## Citation

Cite the benchmark by name, benchmark version, and DOI. The accompanying paper is
cited separately.

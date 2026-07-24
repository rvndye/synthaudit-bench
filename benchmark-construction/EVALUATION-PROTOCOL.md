# SynthAudit-Bench Evaluation Protocol

**Benchmark version:** 1.0.0 (under construction)
**Governs:** how baselines are run, scored, aggregated, reported, and reproduced.
**Binds to:** specification Section 5 (task, matching, metrics, determinism), Section 9 (protocol, reproducibility), and the frozen CLI (`bench audit`, `match`, `report`, `reproduce`, `compliance`).

> Scope note. This protocol specifies the evaluation *procedure*. It runs no detectors and reports no numbers. Every result field below is a placeholder to be filled once the corpus and gold exist.

---

## 1. What is evaluated

The evaluation scores detectors on the Evaluation Corpus `public-dev` split (the public, reproducible score) and, through a sealed procedure, on `held-out`. It uses the frozen scoring: deterministic maximum-cardinality bipartite matching (Section 5.5) and the Section 5.6 metrics. No software changes; the protocol is a way of driving the frozen CLI over the released corpus.

## 2. Baseline detectors

The first release reports a small, principled ladder of baselines so that the benchmark's difficulty is legible. All are run through the frozen detector protocol and entry-point mechanism.

1. **Structural baseline (shipped).** The built-in `StructuralBaselineDetector`, a reference-free, pandas-only detector for the exactly-determinable objective classes it targets (constant column S02, duplicate column A08, duplicate rows S01). It establishes the floor for the easiest objective classes and proves the pipeline runs end to end.
2. **Trivial statistical baselines.** Two deliberately simple detectors, to show that naive approaches do not solve the task: a **correlation-flag** baseline (flag column pairs above a correlation threshold as duplicates or dependencies) and a **single-feature-AUC** baseline (flag a feature as a shortcut when its univariate association with the target is high). These bound the "cheap heuristic" region and exercise the abstention and false-positive behavior against clean negatives.
3. **Reference implementation (optional adapter).** The SynthAudit reference implementation, run through its optional adapter (the `synthaudit` extra), as a strong reference point across all sixteen classes including the adjudicated ones. It is evaluated like any other detector, and it is never used to define gold; its role in scoring is as a participating system, and its only privileged role anywhere is the CS-7 cross-check, which is separate from scoring.

Each baseline declares its capabilities and version and is pinned so the reported numbers are reproducible. Additional third-party detectors register through the same `synthaudit_bench.detectors` entry-point group and are scored identically.

## 3. Execution order

The evaluation runs the frozen pipeline in a fixed order, once per detector, so runs are comparable:

1. **Acquire.** `bench fetch` over the evaluation registry, verifying checksums and honoring the license gate. Fetch-only datasets are materialized locally for the run; the public bundle keeps them as stubs.
2. **Validate.** `bench validate` over the registry, plus the Section 6.1.6 corpus validation, so no run starts on an invalid corpus.
3. **Audit.** `bench audit` runs the detector over the `public-dev` datasets with a fixed root seed (default 42), fixed resource limits, and a recorded configuration hash, writing per-dataset audit results and the run manifest. Datasets are dispatched in the frozen sorted-by-id order; serial and parallel runs produce identical results and an identical manifest hash.
4. **Match.** `bench match` scores the audits against `public-dev` gold, producing the metrics table.
5. **Aggregate and report.** `bench report` assembles the tidy tables, the figures, and (for reporter-conformant detectors) the report cards.
6. **Compliance (separately).** `bench compliance` certifies the detector on the conformance set; this is a gate for a conformance claim, not part of the leaderboard score.

Held-out scoring runs the same steps under seal, recording the held-out instance seeds used, and is executed only by the maintainers.

## 4. Metrics

The reported metrics are exactly the frozen Section 5.6 set; the protocol adds no metric.

- **Detection metrics.** Precision, recall, and F1 at the detection level (did the detector find the artifact on the right support and an acceptable class), with 0/0 defined as 0.
- **Disposition-aware metrics.** The same, additionally requiring the disposition to match.
- **Aggregation levels.** Micro (pooled over all findings), macro-by-class (mean over classes), and macro-by-dataset (mean over datasets). The primary headline number is detection micro-F1 on `public-dev`; macro-by-class and macro-by-dataset are reported alongside to expose class and dataset imbalance.
- **Per-class and per-disposition breakdowns.** F1 per STO class and per disposition, so strengths and weaknesses are visible rather than hidden in an average.
- **Partial-credit secondary metric.** Reported separately and clearly labeled; it is never presented as the primary score.
- **Coverage and abstention.** Counts of `abstain_hit` and `abstain_other`, and the fraction of each gold type recovered. **Objective-gold recall and adjudicated-gold recall are reported separately**, because the benchmark holds objective classes to an exact standard and adjudicated classes to a tolerance.

Clean negatives make precision meaningful: a detector that over-flags is penalized through false positives on the negatives, so recall cannot be traded for nothing.

## 5. Aggregation and the report card

- **Tidy tables.** The frozen aggregation produces deterministic long-format tables (one row per finding, one per dataset, per-STO-class summaries, per-detector summaries, per-dataset metric rows), which are the substrate for every figure and statistic.
- **Report cards and the BTI.** For reporter-conformant detectors, a per-dataset report card is produced with the Benchmark Trustworthiness Index computed exactly as in Appendix D.3 (the weighted geometric mean over available pillars). The BTI is not part of the scored detection task and is never used to rank datasets across different targets; when reported, the probe family is disclosed and cross-implementation BTI comparison is limited to the algebraic pillars unless the probe family matches.
- **Census characterization (separate from scoring).** Over the Census Corpus, the reference implementation produces frame proportions: the exact share of the enumerated frame exhibiting each class. These are frame statistics, not population estimates, and are reported with no sampling confidence intervals (a deliberate design choice); an optional caller-supplied measurement-error bound may be reported but is never fabricated. Census characterization is descriptive and is kept strictly separate from the evaluation score.

## 6. Reporting

- **Public score.** The `public-dev` metrics table, the per-class and per-disposition breakdowns, and the coverage report are published per detector, with the run manifest (versions, configuration hash, environment hash, per-dataset content hashes, seeds, limits) so the numbers are reproducible.
- **Leaderboard hygiene.** The headline is detection micro-F1 on `public-dev`, with objective and adjudicated recall shown separately and clean-negative precision shown explicitly, so a single number cannot hide over-flagging or an inability to handle adjudicated classes.
- **Held-out.** Held-out results are reported in aggregate by the maintainers through the sealed procedure; held-out gold is never published.
- **Results templates.** Reported numbers are recorded in a results table whose columns are fixed here (detector, version, split, detection micro-F1, detection macro-by-class F1, detection macro-by-dataset F1, disposition-aware micro-F1, objective recall, adjudicated recall, clean-negative precision, coverage). The cells are filled only after a real run; this protocol leaves them empty.

## 7. Reproducibility

- **Run manifest.** Every scored run records the benchmark version, STO version, split, detector name and version, configuration including the seed, an environment hash, per-dataset content hashes, and timestamps. A run is reproducible if re-execution under the recorded manifest yields identical tuple sets and identical metrics.
- **Determinism.** Detectors of objective classes operate on the full non-missing data with no sampling; any detector pseudo-randomness is seeded from the configuration seed (default 42) through the normative sampler. Serial and parallel runs are identical by construction.
- **Fresh-environment check.** `bench reproduce` re-runs the pipeline and asserts identical manifest and per-dataset result hashes; `reproduce.yml` runs it on a fresh container. A release reports the reproduction as passing before publication.
- **Resource limits.** Per-dataset wall-clock and memory limits, if imposed, are identical across compared detectors in a run and are recorded in the manifest; a breach yields a `resource` failure and the dataset is excluded from scoring with disclosure.

## 8. Definition of done (evaluation)

The evaluation is release-ready when: the baseline ladder is pinned and registered; the pipeline runs end to end on `public-dev` for every baseline; metrics, breakdowns, and coverage are produced through the frozen CLI; the run manifests are recorded; and the reproduction check passes on a fresh environment. Phase 3 delivers this procedure and the results-table schema; it does not run the baselines or fill any result.

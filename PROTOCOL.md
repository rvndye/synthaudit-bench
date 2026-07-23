# Paper 3 Pre-Registration Protocol (repository copy)

**Version:** 1.0 (pre-data, frozen). **Tag:** `protocol-v1.0`. **Date:** 2026-07-23.

This is the repository-resident, frozen pre-registration for the SynthAudit-Bench
study. It is the revision of the original pre-registration with the three
red-team fatal fixes and the novelty positioning folded in, consistent with the
Final Blueprint and the benchmark specification. It is written to be dated and
frozen before the full corpus is audited. Where this file and the frozen
specification differ, the specification governs.

Any change after freezing is recorded in the research log with rationale and
surfaced in the paper's limitations. Pre-registration exists to make the line
between confirmatory and exploratory claims auditable, not to prevent learning.

---

## 1. Objectives and outcomes

**Goal.** Characterize the presence, class, disposition, and severity of
detectable structural artifacts in public synthetic and simulated tabular
datasets, using SynthAudit v0.1.x as a fixed, reference-free instrument. The
datasets are the study population; the tool is the microscope.

**Framing (fix RT-F1).** This is a **characterization / audit census of a named,
enumerated frame**, not a population prevalence estimate. Results over the census
stratum are reported as **exact proportions of the enumerated frame with no
sampling confidence intervals** (a census has zero sampling error). Where an
interval is reported it represents **instrument measurement uncertainty**
propagated from the adjudicated false-positive and false-negative rates, labeled
as such, never as sampling uncertainty. Generalization beyond the frame is a
stated limitation, not a result. The word "prevalence" is used only as
"prevalence within the enumerated frame".

**Stratification (fix RT-F3).** Every reported result is **stratified by
generator family**. No statistic pools simulator, rule-based, and deep-generative
outputs into a single "synthetic data" number. Low or null structural yield for
deep-generative families is pre-committed for honest reporting and is itself a
finding.

**Primary outcomes** (census stratum, per generator family):
1. Fraction of (dataset, target) units with at least one `target_leakage`
   relation or a critical leakage finding.
2. Fraction graded D or F by the BTI (reported with the pillar vector; the scalar
   never ranks datasets across different targets).
3. Per-artifact-class fraction (the STO classes).

**Secondary / exploratory outcomes** (labeled as such): BTI pillar-vector
distributions; the trivialization ratio where estimable; artifact-class
co-occurrence and dataset clustering; the generator-family signature map; the
instrument's false-positive/false-negative rates and threshold sensitivity.

## 2. Ground truth and the circularity fix (RT-F2)

The instrument is never its own ground truth. Two kinds of gold are used:

- **Objective gold** (algebraic classes): machine-verifiable on the released file
  (an exact identity holds on every row or it does not). Reported as verifiable
  facts; the files are released so anyone can check.
- **Adjudicated gold** (learned-probe classes): established by at least two
  independent human adjudicators applying the STO semantics **without using
  SynthAudit as the oracle**, with disagreements reconciled and inter-adjudicator
  agreement reported.

The scored task, ontology, gold labels, and metrics are defined tool-agnostically
(the benchmark specification). SynthAudit is one baseline among others.

## 3. Sampling frame (hybrid)

Three labeled strata; every dataset carries a `frame_stratum`.

- **Census stratum** (prevalence-within-frame): a completely enumerated
  population from one or two named public repositories, as of a fixed retrieval
  date, filtered by Section 5. The enumeration (repository, query, date) is
  reproducible from a script.
- **Curated supplement** (diversity and generator coverage): purposively selected
  to fill under-covered domains and generator families; used for profile and
  clustering analyses only, never pooled into a frame proportion.
- **Controlled stratum** (generator ground truth): datasets we synthesize with a
  pinned roster of known generators.

## 4. Unit of analysis and target policy

Primary unit: (dataset, designated benchmark target). Multi-target datasets use
the canonical target for the primary analysis; an all-targets sweep is secondary
and reported separately. Target-free datasets are audited in target-free mode and
do not contribute to label-integrity outcomes. Pseudo-replication from a single
generator or source is capped or clustered with cluster-robust variance; the rule
is fixed before auditing.

## 5. Inclusion and exclusion criteria

**Include:** publicly downloadable; tabular and reducible to one analysis table;
produced by a synthesis or simulation step (physics or agent simulator,
statistical model, deep generative model, rule-based fabricator, or resampling);
license permits at least scripted fetch and audit; at least 200 rows and 4
columns; parseable without the original real data.

**Exclude:** purely real/observational with no synthesis step (unless a labeled
negative control); non-tabular primary modality; not license-clearable even for
scripted fetch; interpretation requires the real source; below the size floor.
Grey-zone rulings: SMOTE and augmentation are included as the resampling family;
real-derived-then-simulated data is included with precise provenance labeling;
differential-privacy synthetic releases are included as a subgroup of interest.

## 6. Domain and generator taxonomies

Domains (one primary per dataset): healthcare, finance, insurance, transportation,
energy, manufacturing, government, census, education, cybersecurity, retail,
marketing, iot, environmental-science, general-ml. Effort concentrates
depth-first on roughly six to eight domains reaching n at least 8 to 10; the long
tail is descriptive.

Generator families (with a provenance-confidence flag documented/inferred/
unknown): physics-simulator, agent-based, rule-based, statistical, resampling,
gan, vae, diffusion, llm, unknown. The controlled study supplies documented
exemplars to calibrate inferred labels.

## 7. Metadata, instrument freeze, and analysis

Per-dataset metadata is recorded in the registry and validated against the
dataset schema (fields including `frame_stratum`, `generation_date`,
`generator_version`, and the four transparency booleans). The instrument is
pinned `synthaudit==0.1.x` with version, git SHA, and thresholds recorded in the
run manifest; `selftest --extended` must pass and the 12-cohort numbers must
reproduce. The analysis plan reads only the tidy tables: frame proportions with
instrument measurement-error bounds (no sampling CIs); family-stratified
breakdowns; class co-occurrence and clustering; BTI pillar-vector distribution,
seed stability, and threshold sensitivity; and the validation of the instrument
against the independent gold standard. Exploratory analyses are labeled.

## 8. Quality assurance

A stratified subsample is independently adjudicated; inter-adjudicator agreement
is reported. Genuinely clean or real negative controls are included and expected
to score well. The pinned pipeline must reproduce the reference cohort numbers.
Correlated tool-adjudicator error is disclosed as a limitation that makes the
measurement-error interval a lower bound on uncertainty.

## 9. Novelty positioning

The contribution is claimed as the **reference-free validity framing, the
disposition-aware index, and the released corpus and ontology**, not the
detection algorithms. Approximate functional-dependency and denial-constraint
mining, data profiling, and the leakage literature are prior art and are cited
generously; no algorithmic-novelty claim is made for the miners.

## 10. Reproducibility, ethics, deviations

Pinned Python 3.11 environment (`uv.lock`); `seed=42`; a one-command reproduction;
a run manifest with checksums; a versioned corpus archived with a DOI. Findings
that name a dataset follow the responsible-disclosure procedure. Any deviation
from this protocol after freezing is logged in the research log and surfaced in
the limitations.

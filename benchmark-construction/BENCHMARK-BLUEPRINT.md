# SynthAudit-Bench Benchmark Blueprint

**Benchmark version under construction:** 1.0.0
**Software version (frozen):** synthaudit-bench 0.0.1, tag `v1.0.0-rc1`, archived as v1.0.0
**Status:** construction plan. This document plans the benchmark *content*. It creates no datasets, no gold, and no results.

## 0. Purpose and reading order

The SynthAudit-Bench software is complete and permanently frozen: the specification, the Structural Trustworthiness Ontology (STO), the JSON Schemas, the scoring and matching, the detector protocol, the CLI, and the public API do not change. What does not yet exist is the *benchmark artifact* the software evaluates: the census corpus, the balanced and labeled evaluation corpus, the gold annotations, the held-out split, and the conformance fixtures. Phase 3 constructs that artifact so that a first public benchmark release can be cut.

This blueprint is the master plan. Read it first, then the five companion documents it governs:

1. `CORPUS-PROTOCOL.md` — how the census and evaluation corpora are enumerated, acquired, licensed, versioned, and balanced, and how the held-out split is designed.
2. `ANNOTATION-MANUAL.md` — how two independent annotators produce consistent gold for the adjudicated classes, with decision rules, worked examples, edge cases, adjudication, and quality assurance.
3. `CONFORMANCE-PLAN.md` — how the public compliance fixtures (CS-1..CS-7) are organized, what their published gold and expected outputs are, and the tolerance policy.
4. `EVALUATION-PROTOCOL.md` — how baselines are run, in what order, with what metrics, aggregation, reporting, and reproducibility.
5. `RELEASE-CHECKLIST.md` — everything that must be true before the first benchmark release is tagged, plus versioning, update, deprecation, and governance policy.

The `templates/` directory holds the record, gold, manifest, tolerances, and decision-log templates every workflow fills in.

## 1. What the frozen software fixes (the invariants this plan must satisfy)

Every construction decision below is bound by the frozen specification. The controlling facts:

**Ontology.** Sixteen permanent STO classes in four groups. Thirteen are OBJECTIVE (machine-verifiable on the released file): A01 linear identity, A02 conservation or balance, A03 multiplicative or power-law identity, A04 regime-affine identity, A05 functional dependency, A07 threshold or sign label, A08 duplicate or near-copy column, S01 duplicate rows, S02 constant column, S03 lattice or quantization marginal, S04 uniform-sampled marginal, R01 schedule or row-order leakage, R02 cross-split contamination. Three are ADJUDICATED (they depend on a learned function class and require human judgment): A06 rule-derived discrete label, P01 single-feature dominance, D01 residual near-determinism. Two reserved output symbols exist: `STO-X00` (unclassified suspected structure, scored as an abstention) and `ABSTAIN`.

**Dispositions (four).** `target_leakage`, `structural_constraint`, `redundancy`, `not_applicable`.

**Column roles (eleven), with a fixed precedence.** target, constant, identifier, datetime, duplicate, label_component, derived_deterministic, leaky_feature, near_deterministic, no_signal, input.

**Gold tuple shape (frozen schema).** Required: `support` (a canonical column set or a reserved support token `<ROWS>`/`<TABLE>`), `classes` (array of STO ids), `dispositions` (array), `gold_type` (`objective` or `adjudicated`), `evidence` (string or object). Optional: `optional` (boolean).

**Dataset record shape (frozen schema).** Required: `id` (kebab-case, permanent), `title`, `frame_stratum` (`census` | `planted` | `controlled` | `adjudicated_real`), `domain`, `generator_family`, `provenance_confidence` (`documented` | `inferred` | `unknown`), `modality` (const `tabular`), `task` (`classification` | `regression` | `none`), `target`, `license`, `source`, `loader`, `transparency` (four disclosure booleans), `citation`. Optional: `secondary_domains`, `generator_tool`, `generation_date`, `generator_version`, `secondary_targets`, `test_split`, `notes`.

**Generator-family vocabulary (frozen enum).** physics-simulator, agent-based, rule-based, statistical, resampling, gan, vae, diffusion, llm, unknown.

**Corpus contract (spec Section 6).** Two corpora with different roles. The **Census Corpus** is a reproducibly enumerated frame for characterization; it carries no adjudicated gold and is never scored. The **Evaluation Corpus** is deliberately balanced and labeled and is the scored benchmark; it is drawn from three strata (planted, controlled, adjudicated_real) and must include clean negatives. Identity is the SHA-256 of the canonical UTF-8 CSV. Instances are immutable; corrections create a new instance plus a tombstone. Licensing is fail-closed: data whose license forbids redistribution participates only as a fetch stub with an expected hash.

**Splits (spec Section 6.3.3).** `splits.json` assigns each evaluation dataset to `public-dev` (gold released) or `held-out` (gold withheld). The planted and controlled strata support a *regenerating* held-out partition by re-seeding generators, so the held-out set is not memorizable.

**Gold establishment (spec Section 6.3.4).** Objective gold is machine-verified on the released file and recorded with its evidence. Adjudicated gold is produced by at least two independent human adjudicators applying STO semantics, with no single detector used as an oracle, disagreements reconciled, and inter-adjudicator agreement published.

**Conformance (spec Section 11).** A small, fully public set with published gold and published expected outputs, exercising CS-1 (schema), CS-2 (objective determinism), CS-3 (objective-gold exactness: recall 1.0, objective precision 1.0), CS-4 (adjudicated tolerance: recall and precision at least 0.80), CS-5 (abstention correctness), CS-6 (reproducibility from the lockfile), CS-7 (reference cross-check). Tolerances are version-pinned in `conformance/tolerances.json`.

**Release validation (spec Section 6.1.6).** A corpus release must pass schema validation of every record, referential integrity, hash integrity, split integrity, and the license gate. A release failing any rule must not be tagged.

## 2. Construction principles (the anti-fabrication discipline)

These principles govern every companion document and every future execution step.

**Only build what can be justified.** Every dataset, every gold item, and every reported statistic must trace to a reproducible cause: an objective machine check on the released bytes, a programmatic plant with a known artifact, a pinned generator seed, or a reconciled human adjudication with a published agreement statistic. Nothing is asserted because it is plausible.

**Objective gold is derived, not authored.** For the thirteen objective classes, gold is a machine-verifiable fact about the released file. The corpus process computes it and records the evidence; it never hand-writes an objective label that a check could contradict.

**Adjudicated gold is human, tool-agnostic, and never oracle-driven.** For A06, P01, and D01, gold comes from two independent annotators following `ANNOTATION-MANUAL.md`, not from running the reference implementation and copying its output. The reference implementation may be used only as a post-hoc cross-check (CS-7), clearly labeled as such, never as ground truth.

**Clean negatives are first-class.** The evaluation corpus must contain datasets and columns with no artifact, in a designed proportion, so that a detector cannot score well by over-flagging. Negatives are constructed and documented with the same rigor as positives.

**Planted artifacts are self-certifying.** A planted dataset ships with the generator script and seed that produced its artifact, so its gold is reproducible from source and independently checkable.

**Provenance beats convenience.** Every dataset carries its source URLs, retrieval date, license, and redistributability. Where a license forbids redistribution, the dataset participates as a fetch stub; the reproducibility asymmetry is stated in the manifest.

**Immutability and honest versioning.** Once released, an instance is frozen by content hash. Errors are corrected by minting a new instance and tombstoning the old, never by silently editing bytes.

## 3. Target composition (planning targets, not yet-built content)

The numbers below are construction *targets* with rationale. They set the size and shape of the first release and are recorded here so the corpus process has a definition of done. They are not claims that any dataset exists yet.

**Census Corpus.** A reproducibly enumerated frame of public synthetic and simulated tabular datasets. Target on the order of 100 to 300 datasets, stratified by generator family so that no single ecosystem dominates, with a pre-registered second-repository fallback if the primary frame is too small or too skewed. The census is measured with the frozen reference implementation for characterization; it is never scored and carries no adjudicated gold. The exact target and the enumeration are fixed in `corpus/census/frame.md` before collection begins.

**Evaluation Corpus.** A balanced, labeled set drawn from three strata:

- **Planted** (owned, redistributable): synthetic tables with programmatically known artifacts, one or a few artifacts per table, each with a generator script and seed. This stratum is the objective-gold spine and the primary source of clean negatives.
- **Controlled** (owned, redistributable): outputs of known generators over a small set of shared base tables. The construction budget is at most five base tables crossed with at most seven generator families, with pinned seeds, following the frozen controlled-study design. This stratum probes family signatures.
- **Adjudicated-real** (may be fetch-only): real public tabular datasets with human-adjudicated gold, the stratum that breaks circularity by grounding the adjudicated classes in human judgment rather than any tool.

Class balance across the sixteen classes and the clean-negative fraction are *designed and reported in the manifest* (spec Section 6.3.2). `CORPUS-PROTOCOL.md` fixes the balance targets and tolerances.

**Held-out split.** Every evaluation dataset is assigned in `splits.json` to `public-dev` or `held-out`. Held-out gold is withheld. The planted and controlled strata provide a regenerating held-out partition so the hidden set can be refreshed without leaking.

**Conformance set.** A small, fully public fixture set (on the order of a dozen items) that exercises every CS item: objective positives across the thirteen objective classes, adjudicated positives for A06/P01/D01, clean negatives, and at least one out-of-class artifact for the abstention check. Its gold is published; its expected outputs are a frozen reference cross-check, never ground truth.

## 4. Construction roadmap (order of operations and gates)

The plan follows the frozen execution manual's data work packages. Each stage has a gate that must pass before the next begins.

1. **Controlled vocabularies and templates** (this package). Fix the domain vocabulary, confirm the frozen generator-family vocabulary, and publish the record, gold, manifest, tolerances, and decision-log templates. Gate: templates validate against the frozen schemas.
2. **Census frame** (`corpus/census/frame.md`). Name the repository, the query, the retrieval date, and the enumeration script. Gate: the enumeration is reproducible from the script.
3. **Census inclusion and exclusion** (`corpus/census/inclusion-exclusion.md`). Apply the pre-registered criteria with one logged decision per candidate; apply deduplication and pseudo-replication capping. Gate: every include or exclude decision is logged with a reason.
4. **Acquisition and licensing.** Fetch, checksum, license-clear, and archive where permitted; emit fetch stubs where not. Gate: re-fetch reproduces checksums; the license gate passes.
5. **Planted and controlled construction.** Generate the owned strata with pinned seeds and shipped generator scripts; compute objective gold and its evidence. Gate: every objective gold item is machine-verified on the released bytes.
6. **Adjudicated-real acquisition and annotation.** Acquire the real stratum; run the two-annotator adjudication of `ANNOTATION-MANUAL.md`. Gate: inter-annotator agreement meets the pre-registered thresholds (Cohen kappa at least 0.70 for class presence, at least 0.60 for disposition); disagreements reconciled and logged.
7. **Balance and split assignment.** Verify the designed class balance and clean-negative fraction; assign `public-dev` and `held-out`; confirm no leakage across the split. Gate: balance and split integrity documented and passing.
8. **Conformance set.** Assemble the public fixtures, publish their gold, and freeze the reference expected outputs as a cross-check. Gate: CS-1..CS-7 defined and the fixtures organized per `CONFORMANCE-PLAN.md`.
9. **Baseline evaluation.** Run the baselines under `EVALUATION-PROTOCOL.md` on `public-dev`. Gate: the pipeline runs end to end and reports reproduce under a fresh environment.
10. **Release validation and tag.** Run the spec Section 6.1.6 validation and the `RELEASE-CHECKLIST.md`; tag only if everything passes.

Phase 3 (this package) delivers stage 1 in full and the protocols, templates, and gates for stages 2 through 10. It does not execute stages 2 through 10; the stop condition forbids annotating datasets, fabricating gold, or running detectors.

## 5. How the content plugs into the frozen software

The corpus produced by this plan is consumed by the frozen tools without any software change:

- Records live at `registry/<corpus>/<id>.yaml` and load through `bench validate` and the registry loader.
- Data or fetch stubs live at `corpus/<corpus>/data/<id>/` and are acquired by `bench fetch`.
- Objective and adjudicated gold live at `evaluation/gold/<id>.json` (public split only) and score through `bench match`.
- `evaluation/splits.json` drives the public-dev versus held-out separation.
- Conformance fixtures live under `conformance/` and certify a detector through `bench compliance`, with tolerances pinned in `conformance/tolerances.json`.
- The release bundle is assembled and validated through `bench release`, excluding held-out gold.

The directory layout the release must follow is the normative layout of spec Section 6.1.2. The construction package targets exactly that layout so that the first release drops into place.

## 6. Definition of done for Phase 3

Phase 3 is complete when this package exists and is internally consistent: a blueprint, a corpus protocol, an annotation manual sufficient for two independent annotators, a conformance plan, an evaluation protocol, a release checklist, and the supporting templates and controlled vocabularies, all bound to the frozen schemas and ontology, with no fabricated datasets, gold, or results. The next phase executes the roadmap of Section 4.

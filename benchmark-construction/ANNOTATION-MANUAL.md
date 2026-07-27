# SynthAudit-Bench Gold Annotation Manual

**Benchmark version:** 1.0.0 (under construction)
**Audience:** independent human annotators and adjudicators producing evaluation-corpus gold.
**Goal:** two independent annotators, applying this manual without consulting any detector, produce consistent labels that reconcile into published gold.
**Binds to:** the STO v1.0 register, the four dispositions, the eleven column roles, and the frozen `gold-tuple.schema.json`.

> Scope note. This manual is a protocol. It contains constructed teaching examples that are explicitly labeled as illustrative. It annotates no real dataset and produces no corpus gold. Executing an annotation round is a later phase.

---

## 1. Roles and the tool-agnostic rule

Three roles collaborate, and they are kept separate:

- **Annotator.** Independently assigns gold tuples to a dataset by applying the STO semantics in this manual. Two annotators work on each adjudicated dataset without seeing each other's labels.
- **Adjudicator / reconciler.** Resolves disagreements between the two annotators after both have finished, following Section 8.
- **Gold curator.** Machine-verifies objective gold on the released bytes, checks schema validity and referential integrity, and assembles the final gold files.

**The tool-agnostic rule is absolute.** No annotator, adjudicator, or curator may use any single detector, including the SynthAudit reference implementation, as an oracle for a label. Annotators reason from the class definitions and may use their own general-purpose exploratory analysis (summary statistics, plots, simple regressions they run themselves), but a label is never "because detector X flagged it." The reference implementation appears only later, as a post-hoc cross-check in the conformance suite, and is clearly marked as such.

---

## 2. What is labeled, and by whom

The sixteen STO classes split by how their gold is established.

**Objective classes (thirteen): machine-verified, annotator-confirmed.** A01, A02, A03, A04, A05, A07, A08, S01, S02, S03, S04, R01, R02 are machine-verifiable facts about the released file. For planted datasets the artifact is known by construction; the curator re-verifies it on the released bytes and records the evidence. Annotators do not author objective gold from intuition; they confirm candidates, flag suspected objective artifacts for the curator to verify, and ensure nothing objective is missed. If a machine check and an annotator disagree about an objective class, the machine check on the released bytes governs, and the discrepancy is logged.

**Adjudicated classes (three): human-adjudicated.** A06 rule-derived discrete label, P01 single-feature dominance, and D01 residual near-determinism depend on a learned function class and require human judgment. These are the heart of the annotation round: two independent annotators decide, per the definitions below, whether the semantic condition holds, assign a disposition, and record evidence.

**The open-world symbol.** Suspected structure that fits no class is labeled `STO-X00` and scored as an abstention, never forced into an ill-fitting class.

---

## 3. The gold tuple

Every label is one gold tuple validated against `gold-tuple.schema.json`:

- **`support`** (required): the artifact's locus. Either a canonical set of column names, or a reserved support token: `<ROWS>` for a whole-row artifact (duplicate rows, row-order leakage) or `<TABLE>` for a whole-table property. Column sets are written in canonical sorted order. A support names the columns that *participate in the relation*, not every column in the table.
- **`classes`** (required): one or more STO ids. Multiple ids are used only when the same support genuinely satisfies more than one class and the register does not direct you to a single preferred class (see the precedence rules in Section 6). Where the register says "use X instead of Y," record only X.
- **`dispositions`** (required): one or more of `target_leakage`, `structural_constraint`, `redundancy`, `not_applicable`, assigned per Section 5.
- **`gold_type`** (required): `objective` or `adjudicated`, matching the class.
- **`evidence`** (required): a short human-readable string or a structured object recording *why* the label holds. For objective gold, the machine-verifiable fact (for example, "columns b and c are byte-identical"). For adjudicated gold, the annotator's reasoning and the analysis that supports it. Evidence is mandatory and is published with public-dev gold.
- **`optional`** (optional boolean): set true for an adjudicated item the two annotators could not fully reconcile but agree is plausibly present; an `optional` item never penalizes a detector that misses it (it is excluded from the recall denominator) and never counts as a false positive if found.

The templates in `templates/gold-objective.template.json` and `templates/gold-adjudicated.template.json` show the exact shapes.

---

## 4. Support canonicalization

Consistent support is what lets two annotators' tuples match. Rules:

1. **Column sets are sets, written sorted.** `{b, c}` and `{c, b}` are the same support; write columns in canonical sorted order.
2. **Name a relation by its participants.** For a functional dependency, the support is the determinant set plus the dependent column, because those columns jointly *are* the relation. For a duplicate pair, the support is the two equal columns. For single-feature dominance, the support is the one dominant feature (the target is named in the evidence and disposition, not added to the support).
3. **Whole-row artifacts use `<ROWS>`.** Duplicate rows (S01) and row-order or schedule leakage (R01) use the `<ROWS>` token, not a column list.
4. **Whole-table properties use `<TABLE>`.** Use `<TABLE>` only for a property of the table as a whole with no column locus.
5. **One artifact, one tuple.** Do not split a single relation across several tuples, and do not merge two distinct relations into one support.

---

## 5. Disposition assignment

Disposition captures *what the artifact means for use*, especially its relationship to the nominated target. Assign disposition by this procedure, in order:

1. **Does the artifact leak the target?** If the support (near-)determines the nominated target, or is computed from the target or from a post-outcome quantity, or is a single feature that alone predicts the target near-perfectly, the disposition is `target_leakage`. This covers leaky features, threshold or rule labels that *are* the target's generating rule, single-feature dominance about the target, and residual determinism of the target.
2. **Is the artifact a duplicate or near-copy?** If the artifact is redundant information (duplicate or near-copy column, duplicate rows), the disposition is `redundancy`.
3. **Is the artifact an algebraic or sampling structural property?** If the artifact is a structural identity or constraint of the data generation that is not about the target and not mere redundancy (a conservation or balance identity, a linear or multiplicative identity among features, a lattice or quantization marginal, a uniform-sampled marginal), the disposition is `structural_constraint`.
4. **Otherwise `not_applicable`.** A constant column, or an artifact with no target relationship, no redundancy meaning, and no structural-constraint reading, takes `not_applicable`.

An artifact may carry more than one disposition when more than one genuinely applies (for example, a feature that both duplicates another column and leaks the target), but annotators prefer the single most specific disposition and add a second only with explicit evidence. Disposition is part of what inter-annotator agreement is measured on (Section 8), so apply this procedure literally.

---

## 6. Class catalog and decision rules

The register is the normative source; this section operationalizes it for annotators. Each entry gives the decision rule and the boundary with its neighbors. The objective entries are for candidate-spotting and planted-gold authoring; the adjudicated entries are the focus of the human round.

### 6.1 Group A: algebraic and dependency artifacts

- **A01 Linear identity.** A column is an exact linear combination of others (up to negligible jitter). Support: the columns in the relation. Disposition: usually `structural_constraint`, or `target_leakage` if the identity involves the target. Boundary: a *multiplicative* identity is A03; a *piecewise* linear identity that only holds within regimes is A04.
- **A02 Conservation or balance constraint.** A set of columns sums (or nets) to a constant or to another column, as in a conservation law or an accounting balance. Support: the participating columns. Disposition: `structural_constraint`.
- **A03 Multiplicative (power-law) identity.** A column is a product or power-law function of others. Support: the participating columns. Disposition: `structural_constraint` (or `target_leakage` if it reconstructs the target).
- **A04 Regime-affine identity.** An affine identity that holds within data-defined regimes (piecewise-linear). Support: the participating columns. Disposition: `structural_constraint`.
- **A05 Functional dependency (objective).** A discrete dependent column is determined by a determinant column or minimal set, up to a small violation rate. Decision rule: the violation rate is within the FD tolerance, the dependent is non-degenerate (its modal class is not overwhelming), and the determinant is not a near-key. Exclude dependencies onto near-constant columns (they merely restate imbalance) and key-like determinants. Support: determinant set plus dependent. Disposition: `structural_constraint`, or `target_leakage` if the dependent is the target.
- **A06 Rule-derived discrete label (adjudicated).** See Section 7.1.
- **A07 Threshold or sign label (objective).** A binary column is exactly the indicator of a numeric column crossing a fixed threshold: the two classes occupy disjoint ranges of the numeric column, each class having at least the minimum count. Exclude ultra-rare-class separations and approximate ones. Support: the numeric column plus the binary column. Disposition: `target_leakage` if the binary column is the target, else `structural_constraint`.
- **A08 Duplicate or near-copy column (objective).** Two columns are equal up to sign and negligible jitter (correlation magnitude at or above the duplicate threshold), or two non-numeric columns are identical as strings. Support: the two columns. Disposition: `redundancy`.

### 6.2 Group S: sampling and marginal structure

- **S01 Duplicate rows (objective).** Rows repeat. Support: `<ROWS>`. Disposition: `redundancy`.
- **S02 Constant column (objective).** A column has at most one non-missing value, or is entirely missing. Support: the column. Disposition: `not_applicable`. Boundary: a *near*-constant column is not S02; if it is a rule output it may be A06.
- **S03 Lattice or quantization marginal (objective).** A numeric column's values lie on a regular lattice or show quantization. Support: the column. Disposition: `structural_constraint`.
- **S04 Uniform-sampled marginal (objective).** A column's marginal is a synthetic uniform draw. Support: the column. Disposition: `structural_constraint`.

### 6.3 Group R: order and split leakage

- **R01 Schedule or row-order leakage (objective).** Row order encodes information (a schedule, a sort by the target). Support: `<ROWS>`. Disposition: `target_leakage` if order encodes the target, else `structural_constraint`.
- **R02 Cross-split contamination (objective).** Records appear in more than one released split of the same dataset: at least one companion-split record is present in the primary table under exact match on shared columns, rounded to a stated precision. Requires a companion split (`test_split`). Support: `<ROWS>`. Disposition: `target_leakage`.

### 6.4 Group P: predictive shortcuts

- **P01 Single-feature dominance (adjudicated).** See Section 7.2.
- **D01 Residual near-determinism (adjudicated).** See Section 7.3.

---

## 7. The three adjudicated classes in detail

These require human judgment. For each, apply the decision rule, then record evidence and disposition. Annotators may run their own exploratory analysis but must not copy any single detector's output.

### 7.1 A06 Rule-derived discrete label

**Definition.** A discrete column is, to high fidelity, a deterministic shallow rule (a bounded-depth decision function of thresholds and categories) over other columns.

**Decision rule.** Label A06 when all hold: (a) a shallow rule of bounded depth reproduces the column at high fidelity; (b) the rule removes at least half of the majority-class error, so the fidelity is not just the class prior; and (c) for near-constant columns, only a perfect rule qualifies. Do not label A06 when the apparent fidelity is attributable only to class imbalance, or when the column is an exact univariate threshold (that is A07, objective).

**Boundary with A07 and A05.** If a single numeric threshold separates the classes exactly, it is A07 (objective), not A06. If the dependent is determined by a determinant column up to a small violation rate as a lookup rather than a threshold rule, prefer A05. A06 is for genuine multi-condition shallow rules that need human judgment about "shallow" and "high fidelity."

**Support and disposition.** Support: the rule's input columns plus the derived label column. Disposition: `target_leakage` if the derived label is the nominated target; otherwise `structural_constraint`.

**Illustrative teaching example (constructed, not corpus gold).** A table has `temp`, `pressure`, `vibration`, and `machine_failure`. Exploration shows `machine_failure` is 1 exactly when `temp > 80` or `pressure > 5`, and 0 otherwise, with no exceptions. A shallow two-condition rule reproduces the label perfectly and removes all majority-class error. Label: `{support: [machine_failure, pressure, temp], classes: [STO-A06], dispositions: [target_leakage], gold_type: adjudicated, evidence: "machine_failure = (temp>80) OR (pressure>5), 0 exceptions in the released file"}`.

**Illustrative negative.** If `machine_failure` merely correlates with `temp` and is right 88 percent of the time because 88 percent of rows are class 0, that is class imbalance, not A06.

### 7.2 P01 Single-feature dominance

**Definition.** A single feature alone achieves near-perfect predictive performance on the target, above the majority baseline, indicating a shortcut or a leak.

**Decision rule.** Label P01 when one feature, used alone, achieves a baseline-relative predictive score at or above the single-feature threshold on non-degenerate slices. The score must be *baseline-relative* (improvement over the majority-class or mean baseline), and it must not be an artifact of a degenerate slice or of class imbalance. Judgment is about whether one feature "carries the target on its own."

**Boundary with D01 and A07.** P01 is single-feature. If the target is exactly a threshold on that feature, prefer A07 (objective). If the near-determinism needs several features together and a general learner, that is D01. If one feature alone dominates via a shortcut, that is P01.

**Support and disposition.** Support: the single dominant feature. The target is named in the evidence, not added to the support. Disposition: `target_leakage`.

**Illustrative teaching example (constructed, not corpus gold).** In a churn table, the feature `days_since_cancellation` alone predicts `churned` almost perfectly (it is only defined for churned customers). Alone it lifts far above the majority baseline on the non-degenerate slice. Label: `{support: [days_since_cancellation], classes: [STO-P01], dispositions: [target_leakage], gold_type: adjudicated, evidence: "single-feature baseline-relative score ~1.0 on non-degenerate rows; feature is post-outcome"}`.

**Illustrative negative.** A feature that reaches 0.72 accuracy where the majority baseline is already 0.70 is not dominant; the baseline-relative lift is negligible.

### 7.3 D01 Residual near-determinism

**Definition.** A column is predictable out-of-sample from the others beyond a high threshold by a general, possibly nonlinear, learner, and is not already explained by an A-class identity.

**Decision rule.** Label D01 when a column is predictable out-of-sample from the remaining columns at or above the determinism threshold (a baseline-relative skill for classification, a coefficient of determination for regression), *and* the column is not already covered by A01 through A08. If an exact or near-exact algebraic identity explains the column, report that A-class instead and do not also label D01.

**Boundary with the A classes and P01.** D01 is the residual catch-all for near-determinism that is real but not an identifiable algebraic identity and not single-feature dominance. Always prefer a specific A-class or P01 when it applies; use D01 only for genuine multi-feature nonlinear near-determinism left over.

**Support and disposition.** Support: the predictable column (the evidence names the predictors used). Disposition: `target_leakage` if the predictable column is the target; otherwise `structural_constraint`.

**Illustrative teaching example (constructed, not corpus gold).** A synthetic table has a column `y` that a general learner predicts out-of-sample with a coefficient of determination of 0.98 from a nonlinear combination of five features, with no exact algebraic identity found. Label: `{support: [y], classes: [STO-D01], dispositions: [structural_constraint], gold_type: adjudicated, evidence: "out-of-sample R^2 ~0.98 from a general learner; no A-class identity reproduces y"}`.

---

## 8. Adjudication and disagreement resolution

### 8.1 Independent double annotation

Every adjudicated-real dataset is labeled independently by two annotators who do not see each other's tuples. Each produces a full set of adjudicated gold tuples with evidence and dispositions.

### 8.2 Reconciliation

After both finish, the adjudicator aligns the two label sets by support and class:

1. **Agreements** (same support, same class, same disposition) become gold directly.
2. **Class or disposition disagreements** on the same support are discussed by the two annotators with the adjudicator, using only the definitions and their own evidence, never a detector. If they reach consensus, the reconciled tuple becomes gold and the resolution is logged.
3. **Presence disagreements** (one annotator labeled an artifact the other did not) are examined the same way. If consensus is reached, the tuple is included or dropped accordingly.
4. **Unresolved items** that both annotators agree are plausibly present but cannot be fully reconciled are marked `optional` (they do not penalize a miss and do not count as false positives). Items that cannot be agreed to be present at all are excluded.

Every reconciliation decision is recorded in the audit trail with the reason.

### 8.3 Inter-annotator agreement (pre-registered thresholds)

Agreement is computed and published per release:

- **Class presence**: Cohen kappa at least **0.70**.
- **Disposition**: Cohen kappa at least **0.60**.

These thresholds are pre-registered. If a round falls short, the cause is diagnosed (usually an ambiguous class boundary or an under-specified rule), the manual is clarified, annotators are recalibrated, and the affected datasets are re-annotated before release. The agreement statistic and the reconciliation protocol are published with the release.

---

## 9. Edge cases and tie-breakers

- **Near-constant columns.** Not S02 (which needs at most one non-missing value). A near-constant column qualifies for A06 only under a perfect rule; otherwise it is often `no_signal` and not an artifact.
- **Class imbalance masquerading as skill.** Never label A06, P01, or D01 on fidelity or accuracy that only restates the class prior. All three require baseline-relative evidence.
- **Ultra-rare classes.** A07 and related separations require each class to meet the minimum count; do not label separations that rest on a handful of rows.
- **Key-like determinants.** A functional dependency whose determinant is a near-key is excluded from A05 (a key trivially determines everything).
- **Multi-class acceptable sets.** When a single artifact genuinely satisfies two classes and the register does not direct a single preferred class, list both ids in `classes`; the frozen matcher credits any acceptable class. When the register says "use X instead of Y," record only X.
- **Prefer the specific class.** A-class identity over D01; A07 over A06 for exact univariate thresholds; A05 over A06 for lookup dependencies; P01 over D01 for single-feature dominance.
- **Abstention over forcing.** Suspected structure that fits no class is `STO-X00`, never crammed into the nearest class.
- **Objective machine check wins.** If an annotator's objective judgment conflicts with the curator's machine verification on the released bytes, the machine check governs and the discrepancy is logged.

---

## 10. Quality assurance

- **Pilot and calibration.** Before the main round, both annotators label a small shared calibration set (constructed teaching cases plus a few candidate datasets). Disagreements are discussed and the manual is clarified until calibration agreement clears the Section 8.3 thresholds. The pilot is not part of released gold.
- **Evidence is mandatory.** Every gold tuple carries evidence sufficient for a third party to check it. Objective evidence is the machine-verifiable fact; adjudicated evidence is the reasoning and the annotator's own analysis.
- **Curator verification.** The gold curator re-verifies every objective gold item on the released bytes, validates every tuple against `gold-tuple.schema.json`, and checks referential integrity (every gold id has a record and data or a stub) before the gold enters the release.
- **Audit trail.** The two independent label sets, the reconciliation decisions, the agreement statistics, and the curator checks are retained. Public-dev gold and its evidence are published; held-out gold and the annotators' identities-per-dataset mapping are withheld per the split policy.
- **Oracle-freeness attestation.** The release states that adjudicated gold was produced without using any single detector as an oracle, and that the reference implementation appears only as the CS-7 cross-check.

---

## 11. Annotation record template

Annotators record each dataset's labels using `templates/annotation-record.template.csv` (one row per candidate artifact: dataset id, support, candidate class, disposition, present yes/no, confidence, evidence, annotator id). The two independent records per dataset feed the reconciliation of Section 8. The template is a workflow aid; it holds no labels in Phase 3.

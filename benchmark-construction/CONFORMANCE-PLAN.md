# SynthAudit-Bench Conformance Plan

**Benchmark version:** 1.0.0 (under construction)
**Governs:** the public compliance-suite fixtures and their gold, expected outputs, and tolerances.
**Binds to:** specification Section 11 (CS-1..CS-7), Section 10 (conformance classes), and the frozen `bench compliance` path and `DEFAULT_TOLERANCES`.

> Scope note. This plan specifies how the conformance set is organized and what its published gold and expected outputs mean. It does not run any detector and does not fabricate results. Reference expected outputs are generated later, once the fixtures exist, and only as a labeled cross-check.

---

## 1. Purpose

The conformance suite certifies that a detector is "SynthAudit-Bench v1.0 Detector-conformant." It is a small, fully public set with published gold and published expected outputs, and it is the only thing a conformance claim rests on. Because it is public, it is designed to be *unambiguous*: every objective item has a machine-verifiable answer, and every adjudicated item has published human gold with a stated tolerance. The suite is not a leaderboard; it is a pass/fail (and tolerance) gate.

## 2. The seven items (frozen)

The plan must exercise every CS item exactly as the specification fixes them:

- **CS-1 Schema validation** (pass/fail). Every emitted tuple and every emitted report card validates against the frozen schemas; every consumed record validates. The fixtures include at least one of every artifact shape a detector emits, so a conforming detector's output is exercised against the schema.
- **CS-2 Objective determinism** (pass/fail). Two runs under the same manifest produce byte-identical tuple sets on the required fields. The fixtures are deterministic by construction.
- **CS-3 Objective-gold exactness**. On the fixtures, a conforming detector recovers 100 percent of objective gold (A01 to A05, A07, A08, S01 to S04, R01, R02) at the detection level, with zero objective false positives against the published clean negatives. Tolerance: exact, recall 1.0 and objective precision 1.0, because these are machine-verifiable facts.
- **CS-4 Adjudicated tolerance**. Adjudicated-gold recall (A06, P01, D01) is at least `tau_adj_recall` and adjudicated precision at least `tau_adj_prec`. The v1.0 defaults are 0.80 and 0.80, acknowledging learned-probe variation.
- **CS-5 Abstention correctness** (pass/fail). Suspected-but-unclassified structure is emitted as `STO-X00` or `ABSTAIN` and is not counted against precision. The set includes at least one out-of-class artifact to exercise this.
- **CS-6 Reproducibility** (pass/fail). A fresh environment built from the published lockfile reproduces CS-2 and CS-3.
- **CS-7 Regression (reference cross-check)**. The published expected outputs, a frozen artifact of the reference implementation provided only as a cross-check and never as ground truth, are reproduced for the objective classes within CS-3 tolerance. Disagreements on adjudicated classes are permitted within CS-4.

## 3. Fixture composition

The set is small (on the order of a dozen datasets) and fully public and redistributable (planted or controlled strata only; no fetch-only, no held-out). It is designed to cover, at minimum:

- **Objective positives across all thirteen objective classes.** At least one fixture exhibits each of A01, A02, A03, A04, A05, A07, A08, S01, S02, S03, S04, R01, R02, so CS-3 exercises every objective class. R02 requires a fixture with a companion `test_split`.
- **Adjudicated positives for all three adjudicated classes.** At least one fixture each for A06, P01, D01, with published human gold, so CS-4 has something to score.
- **Clean negatives.** At least one fixture, and clean columns within positive fixtures, that carry no artifact, so CS-3's zero-objective-false-positive requirement is meaningful.
- **At least one out-of-class artifact.** A constructed structure that fits no STO class, so CS-5 can verify that a conforming detector abstains with `STO-X00` rather than forcing a class.

Every fixture is planted or controlled, ships its generator script and seed, and has its objective gold machine-verified on the released bytes. Adjudicated fixtures additionally carry human gold produced under `ANNOTATION-MANUAL.md`.

## 4. Directory organization

The conformance set follows the repository layout the frozen software already expects:

```
conformance/
  datasets/<id>/<id>.csv          # small, fully public conformance datasets (canonical CSV)
  gold/<id>.json                  # published ground truth (objective + adjudicated gold tuples)
  expected/<id>.json              # frozen reference expected outputs (cross-check only, NOT ground truth)
  tolerances.json                 # version-pinned acceptance tolerances (this plan, Section 6)
```

Registry records for conformance fixtures live at `registry/conformance/<id>.yaml` with `frame_stratum: planted` (or `controlled`) and a redistributable license (CC0 or CC BY). Every fixture id is kebab-case and permanent, and every instance is content-hashed like any corpus instance.

## 5. Gold and expected-output policy

Two distinct artifacts must never be confused:

- **`gold/<id>.json` is ground truth.** Objective gold is machine-verified on the released file. Adjudicated gold is human-adjudicated. This is what CS-3 and CS-4 score against.
- **`expected/<id>.json` is a reference cross-check, not ground truth.** It is a frozen snapshot of what the reference implementation emits on the fixture, retained only so CS-7 can detect regressions. A detector that disagrees with `expected/` on an objective class within CS-3 tolerance still passes; a detector that disagrees on an adjudicated class within CS-4 still passes. The expected outputs are generated once, after the fixtures and gold exist, by running the reference implementation, and are clearly labeled as a cross-check. Generating them is a later phase; this plan does not fabricate them.

## 6. Tolerance policy

Acceptance tolerances are version-pinned constants published in `conformance/tolerances.json` and never changed within a benchmark version. The v1.0 defaults, consistent with the frozen `DEFAULT_TOLERANCES`:

- **Objective (CS-3):** exact. `objective_recall = 1.0`, `objective_precision = 1.0`. Machine-verifiable facts admit no tolerance.
- **Adjudicated (CS-4):** `tau_adj_recall = 0.80`, `tau_adj_prec = 0.80`. These acknowledge that adjudicated classes depend on a learned function class.
- **Determinism (CS-2, CS-6):** byte-identical tuple sets on required fields; no numeric tolerance.

Changing any tolerance is a MAJOR benchmark change (it can alter which systems pass) and is governed by the release policy. The tolerances file template is `templates/tolerances.template.json`.

## 7. The compliance result record

A compliance run emits a signed result record `{implementation, version, benchmark_version, results, pass}` whose hash is cited in any conformance claim. This record is produced by the frozen `bench compliance` command; the plan requires only that the fixtures, gold, expected outputs, and tolerances exist and are organized as above so that the command can run.

## 8. Definition of done (conformance set)

The conformance set is release-ready when: every CS item has fixtures that exercise it; every objective gold item is machine-verified on the released bytes; adjudicated gold exists for A06, P01, D01 with published agreement; clean negatives and at least one out-of-class artifact are present; `tolerances.json` is pinned to the v1.0 defaults; and, as a final step performed after the fixtures exist, the reference expected outputs are frozen into `expected/` and labeled as a cross-check. Phase 3 delivers the organization, composition, and tolerance policy; it does not create the fixtures, gold, or expected outputs.

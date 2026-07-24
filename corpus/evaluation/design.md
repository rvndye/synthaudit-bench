# Evaluation Corpus Design (planning document)

Governed by `benchmark-construction/CORPUS-PROTOCOL.md` Section 4. This document
fixes the strata targets, diversity minimums, balance, and generator roster of the
Evaluation Corpus. Targets are design decisions with rationale; no datasets or gold
are created in Phase 3.

## Strata targets

- **planted** (owned, redistributable): REPLACE count. Programmatically known
  artifacts; each ships its generator script and seed. Primary objective-gold spine
  and source of clean negatives.
- **controlled** (owned, redistributable): at most 5 base tables x at most 7
  generators, pinned seeds. Probes family signatures.
- **adjudicated_real** (may be fetch-only): REPLACE count. Human-adjudicated gold
  under the Annotation Manual; grounds the adjudicated classes.

## STO class coverage

Every one of the sixteen classes is represented by multiple positives. The thirteen
objective classes appear in the planted or controlled strata where their gold is
machine-verifiable. Minimum positives per class: REPLACE.

## Diversity minimums (minimum counts per axis)

- Generator family: REPLACE (positives spread across the frozen families).
- Domain: REPLACE (spanning the controlled domain vocabulary).
- Task: both `classification` and `regression`, plus some `none`.
- Size bands: small, medium, larger (all at or above the frozen minimum).
- Transparency: the four disclosure booleans vary across datasets.

## Balance and clean negatives

- Class-balance design: REPLACE (per-class target counts; no class dominates).
- Clean-negative fraction target: REPLACE (datasets and columns with no artifact),
  pinned in `MANIFEST.json` before construction.
- Balance is an evaluation-corpus property only, never a census base rate.

## Generator roster (controlled stratum)

- Base tables (at most 5): REPLACE (small, well-understood public tables).
- Generators (at most 7): REPLACE (spanning several frozen families, for example a
  statistical baseline, a copula or resampling method, a GAN, a VAE, and a diffusion
  or LLM tabular generator), each with a pinned seed and recorded tool and version.

## Definition of done

- [ ] All three strata populated to their designed minimums.
- [ ] Every STO class represented by multiple positives.
- [ ] Clean negatives present at the designed fraction; balance within tolerance.
- [ ] Diversity minimums met; roster and seeds pinned and cited.
- [ ] Objective gold machine-verified; adjudicated gold meets agreement thresholds.

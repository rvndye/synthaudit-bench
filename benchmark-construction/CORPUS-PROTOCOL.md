# SynthAudit-Bench Corpus Protocol

**Benchmark version:** 1.0.0 (under construction)
**Governs:** the Census Corpus, the Evaluation Corpus, and the held-out split.
**Binds to:** specification Section 6 (corpus), Section 7 (dataset record), the frozen `dataset.schema.json`, and the frozen generator-family and stratum vocabularies. This is a construction protocol; it produces no datasets.

---

## 1. Scope and the two-corpus contract

SynthAudit-Bench has two corpora with deliberately different roles, and conflating them is a defined error.

The **Census Corpus** is a reproducibly enumerated frame of public synthetic and simulated tabular datasets. Its purpose is characterization: measuring how structural artifacts occur across a named frame using the frozen reference implementation. It carries no adjudicated gold, it is never used to score a detector, and prevalence statistics computed over it are statistics of that enumerated frame, not estimates of a population.

The **Evaluation Corpus** is the scored benchmark. It is deliberately balanced and labeled, drawn from three strata, and it must contain clean negatives. Its class balance is a designed property that is reported in the manifest and must never be read as a census base rate.

Both corpora share the common requirements of Section 2, then diverge in Sections 3 (census) and 4 (evaluation). Section 5 fixes the split. Section 6 fixes the metadata. Section 7 fixes versioning and deprecation.

---

## 2. Common requirements (every dataset in either corpus)

### 2.1 Identity

Every dataset has a stable, lowercase kebab-case `id` that is unique and permanent within the corpus. An instance is additionally and immutably identified by the SHA-256 content hash of its canonical CSV serialization. The `id` names the dataset across versions; the content hash names one immutable instance of it.

### 2.2 Canonical serialization

Tabular data must be representable as UTF-8 CSV with a header row, `\n` line endings, a comma delimiter, RFC 4180 quoting, and no byte-order mark. The content hash is computed over this canonical form. A Parquet copy may be shipped in addition, but the canonical CSV defines identity and every checksum. The frozen loader reads this canonical form faithfully, so the loaded content hash equals the manifest instance identity.

### 2.3 Provenance and licensing (fail-closed)

Every record must carry the original source URLs, the retrieval date, a license identifier with an SPDX code, a `redistribute` flag, and a `fetch_scriptable` flag. Where redistribution is not permitted, the dataset participates as a **fetch stub**: the record ships the fetch specification and the expected content hash instead of the bytes. The maintainers never redistribute data whose license forbids it. The reproducibility asymmetry, redistributable synthetic-truth data versus fetch-only licensed data, is stated in the manifest.

### 2.4 Acquisition protocol

Acquisition is registry-driven, cached, checksum-verified, and license-gated, and it runs through the frozen `bench fetch` path (no new software). The protocol per candidate:

1. Read the record's `source.urls` and `source.sha256`.
2. If the license permits redistribution and scripted fetch, fetch each file through the injected transport, write it to the content-addressed cache, and verify it against its declared SHA-256. A mismatch deletes the fetched bytes and fails closed.
3. Archive the verified bytes where the license permits (durability against source rot).
4. If the license forbids redistribution, do not fetch into the release; emit or retain the fetch stub with the expected hash.
5. Record the retrieval date and the resolved license in the record.

Re-running acquisition on an unchanged registry must reproduce identical checksums; this is a release gate.

### 2.5 Checksums and the manifest

`MANIFEST.json` lists, for every instance: `id`, canonical `sha256`, byte size, row and column counts, corpus (`census` or `evaluation`), split, license, and source. A release is valid only if every present data file matches its manifest hash and every fetch stub declares an expected hash. The manifest also states the reproducibility asymmetry of Section 2.3 and, for the census, the enumeration provenance of Section 3.1.

---

## 3. Census Corpus

### 3.1 Frame definition (reproducible enumeration)

The census is an enumerated frame, not a convenience sample, so the frame must be reproducible from a script. Before any collection, `corpus/census/frame.md` fixes:

- the **named source repository or repositories** (for example, a public dataset registry) and the exact **query** used to enumerate candidates;
- the **retrieval date**;
- the **enumeration script** that, given the query and date, returns the candidate list deterministically;
- a **pre-registered second-repository fallback** to invoke if the primary frame is too small or too skewed toward one generator ecosystem.

The enumeration provenance is recorded in the manifest so that a third party can reconstruct the frame.

### 3.2 Inclusion criteria

A candidate is included only if all of the following hold, and the decision is logged:

- it is a **tabular** dataset (rows and typed columns) representable in the canonical CSV form;
- it is **synthetic or simulated** (produced by a generator, a simulator, or a resampling procedure), not a raw real-world measurement dataset;
- it is **publicly accessible** under a license that at least permits scripted fetch for research, so it can participate as data or as a fetch stub;
- it meets the frozen minimum size (at least the below-minimum thresholds the loader enforces), so it is not degenerate;
- its **generator family** can be assigned from the frozen vocabulary with a stated `provenance_confidence`.

### 3.3 Exclusion criteria

A candidate is excluded, with a logged reason, if any of the following hold:

- it is **not tabular** (image, text, graph, or free-form), or cannot be serialized to canonical CSV;
- it is a **raw real-world** dataset with no generative or simulated component (those belong, if anywhere, to the adjudicated-real evaluation stratum, not the census);
- its **license forbids even scripted fetch**, so it cannot participate as data or as a verifiable stub;
- it is a **near-duplicate** of an already-included instance beyond the deduplication threshold of Section 3.4;
- its **provenance is unrecoverable** to the point that no generator family can be assigned even as `unknown` with a documented basis.

### 3.4 Deduplication and pseudo-replication capping

Public repositories over-represent a few popular base tables re-uploaded by many users. To keep the frame from being dominated by pseudo-replicates, apply pre-registered capping:

- compute the canonical content hash; drop exact duplicates;
- detect near-duplicates (same schema and near-identical marginals) and cap the number of near-duplicate instances of any single underlying table at a pre-registered limit;
- cap the share of any single generator ecosystem so that no one tool dominates the frame, invoking the second-repository fallback if a cap cannot be met.

Every capping action is logged.

### 3.5 Census metadata and stratification

Every census record carries `frame_stratum: census`, a `domain`, a `generator_family`, and a `provenance_confidence`. The frame is stratified by generator family so that characterization is not driven by one ecosystem. The census carries no gold and is never scored; its only output is characterization measured with the frozen reference implementation.

### 3.6 Census target and definition of done

The construction target is a frame on the order of 100 to 300 datasets stratified across generator families, with the exact target fixed in `frame.md`. The census stage is done when: the enumeration is reproducible from the script; every include or exclude decision is logged with a reason; deduplication and capping are applied and documented; and the target n is reached or a documented shortfall triggers the pre-registered contingency.

---

## 4. Evaluation Corpus

### 4.1 Composition (three strata)

The evaluation corpus is drawn from three strata, each labeled in `frame_stratum`:

- **planted**: synthetic tables with programmatically known artifacts. Owned and redistributable. Each planted dataset ships the generator script and seed that produced its artifact, so its objective gold is reproducible from source.
- **controlled**: outputs of known generators. Owned and redistributable. Built as at most five shared base tables crossed with at most seven generator families, with pinned seeds, following the frozen controlled-study design.
- **adjudicated_real**: real public datasets with human-adjudicated gold. May include fetch-only datasets. This is the stratum that grounds the adjudicated classes in human judgment and breaks circularity.

The planted and controlled strata are the objective-gold spine and the source of clean negatives; the adjudicated-real stratum supplies adjudicated gold under `ANNOTATION-MANUAL.md`.

### 4.2 Sampling and diversity strategy

The evaluation corpus is *constructed to a design*, not sampled from the census. The design targets diversity along the axes the frozen record already encodes, so a detector cannot overfit a narrow slice:

- **STO class coverage**: every one of the sixteen classes is represented by multiple positive instances, and the thirteen objective classes are represented in the planted or controlled strata where their gold is machine-verifiable.
- **Generator-family coverage**: positives are spread across the frozen generator families rather than concentrated in one.
- **Domain coverage**: positives span the controlled domain vocabulary of Section 6.3.
- **Task coverage**: both `classification` and `regression` targets appear, plus `none` for datasets audited without a nominated target.
- **Size coverage**: small, medium, and larger row and column counts appear, all at or above the frozen minimum.
- **Transparency coverage**: the four disclosure booleans vary across datasets so the transparency pillar is exercised.

Diversity targets are expressed as minimum counts per axis in the manifest, not as claims about any population.

### 4.3 Balancing strategy and clean negatives

Class balance is a designed and reported property of the evaluation corpus (spec Section 6.3.2). The balancing rules:

- the distribution of gold classes is designed so that no single class dominates recall or precision, and the design is recorded in the manifest;
- **clean negatives are mandatory**: a designed fraction of datasets, and of columns within positive datasets, carry no artifact, so a detector cannot achieve high recall by over-flagging. The target clean-negative fraction is fixed in the manifest before construction and is treated as a first-class quantity;
- balance is a property of the evaluation corpus alone and is never conflated with census base rates.

The concrete per-class minimums and the clean-negative fraction are pinned in `MANIFEST.json` at construction time using the template in `templates/MANIFEST.template.json`.

### 4.4 Generator roster (controlled stratum)

The controlled stratum uses a pinned roster: at most five base tables, each a small, well-understood public table, crossed with at most seven generators spanning several frozen generator families (for example a statistical baseline, a copula or resampling method, a GAN, a VAE, and a diffusion or LLM tabular generator, subject to license and availability). Every generator run pins its seed and records its tool and version in the record (`generator_tool`, `generator_version`, `generation_date`). The roster and seeds are cited so the outputs are reproducible.

### 4.5 Domains and sizes

Datasets are tagged with a `domain` from the controlled vocabulary of Section 6.3 and, where relevant, `secondary_domains`. Sizes span at least three bands (small, medium, larger) so that below-minimum handling, typical operation, and scale are all exercised, always at or above the frozen minimum row and column counts.

### 4.6 Gold establishment

- **Objective gold** (thirteen classes) is machine-verified on the released file and recorded with its evidence. For planted datasets the artifact is known by construction and independently re-verified on the released bytes; the gold is never hand-authored in a way a check could contradict.
- **Adjudicated gold** (A06, P01, D01) is produced by at least two independent human annotators applying STO semantics under `ANNOTATION-MANUAL.md`, with no single detector used as an oracle. Disagreements are reconciled; inter-annotator agreement is reported; items that cannot be reconciled are marked `optional` or excluded.

Gold files follow the frozen `gold-tuple.schema.json` and the templates in `templates/`.

### 4.7 Definition of done (evaluation corpus)

The evaluation corpus stage is done when: all three strata are populated to their designed minimums; every objective gold item is machine-verified on the released bytes with recorded evidence; adjudicated gold meets the agreement thresholds of `ANNOTATION-MANUAL.md`; the clean-negative fraction and class balance match the manifest design within tolerance; and referential integrity holds (every gold id has a record and data or a stub).

---

## 5. Held-out split

### 5.1 Design and the four logical roles

`evaluation/splits.json` assigns each evaluation dataset to `public-dev` or `held-out`. Around this frozen two-way split, the benchmark distinguishes four logical roles, mapped onto the two physical partitions so that no new software is needed:

- **train / tuning material**: any external data a detector author uses to build or tune a detector. This is outside the benchmark entirely; the benchmark supplies no training labels.
- **validation (public-dev)**: the `public-dev` partition, whose gold is released. Detector authors use it to self-check and to reproduce the published baseline numbers.
- **benchmark (public-dev scoring)**: scoring on `public-dev` is the public, reproducible score.
- **hidden evaluation (held-out)**: the `held-out` partition, whose gold is withheld and evaluated only by the maintainers or through a sealed procedure.

### 5.2 Reproducible partitioning and seed policy

Split assignment is deterministic and fixed within a benchmark version. The assignment is produced by a documented, seeded procedure (the benchmark seed, default 42) over the stable dataset ids, so the partition is reproducible and independent of file order. The seed and the procedure are recorded with the release. The frozen software already derives per-dataset seeds deterministically from the root seed and the dataset id, so held-out re-seeding composes with the existing machinery.

### 5.3 Leakage prevention

Leakage across the split is prevented and checked:

- **no shared base table across the split without disclosure**: a base table used to build a `public-dev` instance and a `held-out` instance must be tracked, and cross-split contamination (STO-R02) between partitions is treated as a defect unless it is the deliberately planted subject of a gold item within a single dataset's companion split;
- **companion splits stay within a dataset**: the `test_split` companion used to probe STO-R02 belongs to one dataset record and never crosses the public/held-out boundary;
- **no gold leakage**: held-out gold is never shipped in the public bundle; `bench release` excludes it;
- **split integrity is a release gate** (spec Section 6.1.6).

### 5.4 Regenerating held-out

Because the planted and controlled strata are generated from scripts and seeds, the maintainers may mint fresh held-out instances by re-seeding the generators. This keeps the hidden set non-memorizable across time without changing the benchmark version's fixed public assignment. Held-out scoring records the held-out instance seeds used, so a sealed evaluation is itself reproducible.

### 5.5 Versioning of the split

Split assignment is fixed within a benchmark version. Reassigning a dataset between `public-dev` and `held-out` is a MAJOR benchmark change (it can alter a conforming system's comparability), and is governed by Section 7.

---

## 6. Metadata

### 6.1 Record fields

Every dataset is described by one YAML record validated against the frozen `dataset.schema.json`, with the required and optional fields listed in the Blueprint Section 1 and demonstrated in `templates/dataset-record.template.yaml`. Records live at `registry/<corpus>/<id>.yaml`.

### 6.2 Controlled generator-family vocabulary (frozen)

`generator_family` is drawn only from the frozen enum: physics-simulator, agent-based, rule-based, statistical, resampling, gan, vae, diffusion, llm, unknown. `unknown` is used only with a documented basis and an honest `provenance_confidence`.

### 6.3 Controlled domain vocabulary (this protocol)

The specification defers the domain vocabulary to the corpus. This protocol fixes a closed, extensible domain vocabulary for v1.0 so that `domain` is comparable across records. The v1.0 vocabulary:

`finance`, `healthcare`, `energy`, `mobility`, `industrial`, `retail`, `telecom`, `social`, `environment`, `government`, `education`, `scientific`, `synthetic`, `other`.

`synthetic` denotes an abstract or generator-native table with no real-world domain; `other` is used only with a note explaining why no listed domain fits. Adding a domain term is an additive MINOR change (Section 7). The vocabulary is published in `templates/controlled-vocabularies.md`.

### 6.4 Transparency booleans

The four `transparency` booleans (`generator_described`, `generator_code_available`, `seed_reported`, `artifacts_disclosed`) are recorded honestly per dataset. They feed the frozen transparency pillar and must reflect what is actually disclosed by the source, not what would be convenient.

### 6.5 Provenance confidence

`provenance_confidence` is `documented` (the generator and its configuration are recorded at the source), `inferred` (assigned from strong but indirect evidence), or `unknown` (no reliable basis; used sparingly and with a note).

---

## 7. Versioning, immutability, and deprecation

### 7.1 Instance immutability

A released instance is immutable, identified by its content hash. Data is never silently mutated or deleted, so prior benchmark versions stay reproducible.

### 7.2 Corrections via tombstones

A correction creates a new instance with a new id or a new content hash and deprecates the old one via a tombstone record `{id, deprecated: true, reason, replaced_by, since_version}`. The old bytes remain available so that results reported against them can still be reproduced.

### 7.3 Benchmark SemVer for corpus changes

Corpus changes follow the benchmark SemVer of specification Section 12.2:

- **MAJOR**: anything that can alter a conforming system's score or break prior gold or outputs, including removing datasets, reassigning the split, or changing gold.
- **MINOR**: additive changes, including adding datasets, adding a domain term, or adding clean negatives, that do not alter existing gold or scores.
- **PATCH**: fixes that change neither gold nor scores, such as a metadata typo or an added citation.

### 7.4 Release validation gate

No corpus release is tagged unless it passes, in full, the spec Section 6.1.6 validation: schema validation of every record, referential integrity, hash integrity, split integrity, and the license gate. The `RELEASE-CHECKLIST.md` operationalizes this gate.

---

## 8. Operational planning documents

This protocol is executed through the operational documents seeded in the repository:

- `corpus/census/frame.md` — the census frame enumeration (repository, query, retrieval date, script, fallback).
- `corpus/census/inclusion-exclusion.md` — the census inclusion and exclusion criteria and the per-candidate decision log.
- `corpus/evaluation/design.md` — the evaluation corpus design: strata targets, diversity minimums, balance, clean-negative fraction, generator roster, and size bands.

Each references this protocol and is filled in during construction; none is populated with datasets or gold in Phase 3.

# Census Frame Definition (TEMPLATE / planning document)

Governed by `benchmark-construction/CORPUS-PROTOCOL.md` Section 3. This document
fixes the reproducible enumeration of the Census Corpus frame **before** any
collection. It is filled in during construction; it lists no datasets in Phase 3.

## Frame provenance (fill in before collection)

- **Primary repository:** REPLACE (a named public dataset registry).
- **Enumeration query:** REPLACE (the exact query or filter that returns candidates).
- **Retrieval date:** REPLACE (ISO-8601).
- **Enumeration script:** REPLACE (path to the deterministic script that, given the
  query and date, returns the candidate list; the script is committed and cited).
- **Second-repository fallback:** REPLACE (the pre-registered fallback repository and
  query to invoke if the primary frame is too small or too skewed toward one
  generator ecosystem).

## Target

- **Target n:** REPLACE (on the order of 100 to 300, per the Blueprint), stratified
  by generator family.
- **Stratification plan:** REPLACE (target share per generator family; caps per
  ecosystem).

## Reproducibility statement

The frame must reproduce from the script above given the query and retrieval date.
The enumeration provenance is copied into `MANIFEST.json` at release. Prevalence
statistics computed over this frame are statistics of the enumerated frame, not
population estimates.

## Definition of done

- [ ] Repository, query, retrieval date, and script fixed and committed.
- [ ] Enumeration reproduces from the script.
- [ ] Second-repository fallback pre-registered.
- [ ] Target n and stratification plan fixed.

# Census Inclusion and Exclusion (planning document)

Governed by `benchmark-construction/CORPUS-PROTOCOL.md` Section 3. Every candidate
from the frame (`frame.md`) is decided here with a logged reason, using
`benchmark-construction/templates/census-decision-log.template.csv`. No decisions
are recorded in Phase 3.

## Inclusion criteria (all must hold)

1. Tabular (rows and typed columns), representable as canonical UTF-8 CSV.
2. Synthetic or simulated (generator, simulator, or resampling output), not a raw
   real-world measurement dataset.
3. Publicly accessible under a license that at least permits scripted fetch for
   research (participates as data or as a fetch stub).
4. At or above the frozen minimum size (not degenerate).
5. Generator family assignable from the frozen vocabulary, with a stated
   `provenance_confidence`.

## Exclusion criteria (any triggers exclusion)

1. Not tabular, or not serializable to canonical CSV.
2. Raw real-world dataset with no generative or simulated component.
3. License forbids even scripted fetch (cannot participate as data or a verifiable
   stub).
4. Near-duplicate beyond the capping threshold (Section 3.4).
5. Provenance unrecoverable to the point no generator family can be assigned, even
   as `unknown` with a documented basis.

## Deduplication and capping (pre-registered)

- Drop exact content-hash duplicates.
- Cap near-duplicate instances of any single underlying table at REPLACE (limit).
- Cap the share of any single generator ecosystem at REPLACE (share); invoke the
  second-repository fallback if a cap cannot be met.

## Decision log

Maintained in the decision-log CSV (one row per candidate: id, source, retrieved,
decision, reason, generator family, provenance confidence, duplicate-of, capping
action). Every include and exclude decision is logged with a reason.

## Definition of done

- [ ] Every frame candidate decided and logged with a reason.
- [ ] Deduplication and capping applied and documented.
- [ ] Target n reached or a documented shortfall with the contingency invoked.

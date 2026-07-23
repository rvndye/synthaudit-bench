# conformance/

The public compliance-suite fixtures used to certify a conforming implementation
(specification CS-1..CS-7).

- `datasets/` — small, fully public conformance datasets.
- `gold/` — their published ground truth.
- `expected/` — frozen expected outputs of the reference implementation, provided
  as a cross-check only, never as ground truth.
- `tolerances.json` — version-pinned acceptance tolerances.

An implementation is compliant for a version if it passes every suite item on
this set. Populated in the release work package.

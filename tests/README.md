# tests/

Eight test tiers, one per subdirectory:

- `unit/` — pure modules in isolation (property-based where useful).
- `integration/` — pipeline stage chains on small fixtures.
- `regression/` — the reference cohort numbers reproduced within tolerance.
- `golden/` — frozen expected outputs for the conformance datasets.
- `schema/` — every schema validates its valid and invalid fixtures.
- `conformance/` — the specification compliance suite (CS-1..CS-7).
- `performance/` — runtime and memory budgets.
- `reproducibility/` — identical inputs yield identical outputs.

Coverage target: at least 85% on the library. Run `python -m pytest` or
`make test`.

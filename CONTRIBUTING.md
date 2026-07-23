# Contributing

Thank you for helping build SynthAudit-Bench. This is scientific infrastructure
intended to be maintained for many years; correctness, determinism, and
reproducibility come before speed.

## Development setup

```bash
python -m pip install -e ".[dev]"
make check
```

`make check` runs lint (ruff), format check, type check (mypy, strict), the
import contracts (import-linter), and the tests with coverage. Every commit
should leave the repository in a passing state.

## Branches and commits

- Branch per Execution Manual work package: `wp<NN>/<kebab-slug>`
  (for example `wp1/sto-spec`). Maintenance branches use `fix/…`, `docs/…`,
  `chore/…`.
- `main` is protected; no direct pushes.
- Use [Conventional Commits](https://www.conventionalcommits.org/) with a work
  package scope: `type(wpN): summary` (types: `feat, fix, docs, data, exp,
  test, chore, refactor`). Reference issues in the footer (`Refs #NN`).
- Small commits; no "everything" commits.

## Pull request checklist

- [ ] Linked to an issue and milestone.
- [ ] CI green (lint, format, type, import contracts, tests, schema validation).
- [ ] Tests added or updated for code changes; a fixed bug has a regression test.
- [ ] Docs updated; touched directories keep a current `README.md`.
- [ ] No prohibited wording introduced into manuscript text (see the claims
      ledger in the Final Blueprint).
- [ ] Reproducibility preserved (no unpinned deps; no unseeded randomness).
- [ ] The work package quality gate items touched are satisfied or explicitly
      deferred with a tracked follow-up issue.

## Engineering standards

Typed, documented, modular, deterministic. Avoid global state and hidden side
effects. Favor pure functions and composition over inheritance. Every public
module has tests; every schema ships valid and invalid fixtures; every
deterministic algorithm has a repeatability test. Coverage target: at least 85%.

## Extending the benchmark

New detectors, ontology class packs, tasks, corpora, and figures are added
through the plugin entry-point groups (see the software architecture), never by
editing core modules. Out-of-scope ideas (a future paper, a future tool version,
a future benchmark or ontology revision) are recorded in `docs/future-work.md`,
not implemented.

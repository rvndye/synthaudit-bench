# src/synthaudit_bench/

The benchmark library. Modules follow the one-way layering in the software
architecture: pure domain (`model`, `sto`, `schemas`, `errors`) inward of pure
infrastructure (`canonical`, `sampler`, `determinism`, `logging`, `config`)
inward of pure transforms (`registry`, `load`, `gold`, `aggregate`, `stats`,
`reportcard`, `figures`) inward of effectful modules (`acquire`, `runner`,
`release`, `compliance`) inward of composition (`cli`). Imports never flow back
outward, enforced by the import-linter contract.

**Prime directive:** this package is detector-agnostic and never imports the
SynthAudit reference implementation. A conforming detector is supplied through
the `detector` plugin interface; the optional SynthAudit adapter is the only
module permitted to import `synthaudit`.

At WP0 the package contains only the version source; modules are added one work
package at a time.

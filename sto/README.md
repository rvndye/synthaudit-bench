# sto/

The **Structural Trustworthiness Ontology (STO)**, a standalone, versioned
standard that may be cited and used independently of the benchmark.

The register content (identifiers, definitions, scope, inclusion and exclusion
criteria, examples, counterexamples, relationships, and gold type per class):

- `STO-<version>.json` — the normative class register.
- `schema/sto.schema.json` — the schema the register validates against.

**Canonical location.** So that an installed `synthaudit_bench` package can load
its own ontology, the canonical register and schema ship as package data at
`src/synthaudit_bench/sto_data/` and are loaded through `synthaudit_bench.sto`.
A release bundle materializes the published copies into this `sto/` directory.

Class identifiers are permanent; incompatible redefinition requires a new
identifier and deprecation of the old (see `GOVERNANCE.md`).

# The Structural Trustworthiness Ontology (STO)

STO is a standalone, versioned standard. It may be cited and used independently of
the benchmark and of any detector. This page explains its philosophy, its
versioning and compatibility guarantees, how to extend it, and how to use the
Python API. The normative content is the register at
`src/synthaudit_bench/sto_data/STO-1.0.0.json`, validated against
`sto_data/sto.schema.json`.

## Philosophy

**Semantics over algorithm.** Each class is defined by what the artifact *is* as a
property of a released table. The recommended detector tolerances (referenced by
each class as `operating_points`) are defaults for a detector, not the definition
of the class and not ground truth. A conforming implementation may use any method
to detect a class.

**Objective versus adjudicated gold.** A class is `objective` when its presence is
machine-verifiable on the file (linear algebra, exact arithmetic, counting) and
`adjudicated` when it depends on a learned function class and requires human
judgment. STO v1.0 marks three classes adjudicated: `STO-A06` (rule-derived
labels), `STO-P01` (single-feature dominance), and `STO-D01` (residual
near-determinism).

**Disposition is a separate axis.** Class membership is a property of the table.
The `disposition` (target leakage, structural constraint, redundancy, or not
applicable) is the relation of an artifact to a nominated target. The two are
reported independently.

**Open world.** STO does not claim to enumerate every possible artifact. A
detector may report suspected-but-unclassified structure with the reserved symbol
`STO-X00`; the reserved symbol `ABSTAIN` marks an explicit abstention. Neither is
a class.

## Classes

Sixteen classes in four groups. Group A (deterministic column relations): linear
identity, conservation or balance constraint, multiplicative identity,
regime-affine identity, functional dependency, rule-derived label, threshold or
sign label, duplicate or near-copy column. Group S (sampling and marginal
properties): duplicate rows, constant column, lattice or quantization marginal,
uniform-sampled marginal. Group R (ordering and cross-split leakage): schedule or
row-order leakage, cross-split contamination. Group P (predictive shortcuts):
single-feature dominance, residual near-determinism. Each class carries a stable
identifier, definition, scope, inclusion and exclusion criteria, an example, a
counterexample, relationships, its gold type, and operating-point pointers.

## Versioning and compatibility

STO is versioned independently of the benchmark and the software, using semantic
versioning:

- **Class identifiers are permanent** and are never redefined incompatibly.
- **Adding a class is a MINOR change** (backward compatible). Removing or
  redefining a class is **MAJOR**.
- An available version *satisfies* a required version when they share a MAJOR
  version and the available version is at least the required version (additive
  minor compatibility). See `Version.satisfies`.
- Deprecated classes are retained with a replacement pointer and the version of
  deprecation, so prior benchmark versions remain reproducible.

## Extension process

New classes are proposed through the governance change process (`GOVERNANCE.md`).
A proposal must specify every register field and a gold type, must use a new
permanent identifier, and must not overlap an existing class without an explicit
relationship note. Third-party class packs register through the ontology plugin
entry point rather than by editing the core register.

## API usage

```python
from synthaudit_bench import sto

onto = sto.load()                      # cached, validated, immutable
onto.version                           # Version(1, 0, 0)
onto.class_ids                         # ('STO-A01', ..., 'STO-D01')
cdef = onto.get("STO-A07")             # ClassDef; raises OntologyError if unknown
cdef.name                              # 'Threshold or sign label'
onto.is_objective("STO-A07")           # True
onto.is_objective("STO-A06")           # False (adjudicated)
onto.gold_type("STO-P01")              # GoldType.ADJUDICATED
onto.classes_in_group(...)             # classes in a group
onto.is_deprecated("STO-A01")          # False in v1.0
onto.traceability_for("STO-A03")       # reference-implementation field (documentation)
sto.available_versions()               # ('1.0.0',)
```

The loader validates the register against the STO schema on load and enforces
structural invariants (unique identifiers, relationship and replacement
references, complete role precedence, complete traceability). Loading is
deterministic: the same version always yields an equal ontology.

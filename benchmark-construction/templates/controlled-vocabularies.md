# Controlled Vocabularies (benchmark v1.0.0)

These closed vocabularies make dataset records comparable. Two are frozen by the
software; one is fixed by the Corpus Protocol for this benchmark version.

## Generator family (FROZEN by the software enum)

`physics-simulator`, `agent-based`, `rule-based`, `statistical`, `resampling`,
`gan`, `vae`, `diffusion`, `llm`, `unknown`.

Use `unknown` only with a documented basis and an honest `provenance_confidence`.
This vocabulary is part of the frozen software and cannot change in v1.0.

## Frame stratum (FROZEN by the software enum)

`census`, `planted`, `controlled`, `adjudicated_real`.

## Provenance confidence (FROZEN by the software enum)

`documented`, `inferred`, `unknown`.

## Task (FROZEN by the software enum)

`classification`, `regression`, `none`.

## Domain (fixed by the Corpus Protocol for benchmark v1.0)

`finance`, `healthcare`, `energy`, `mobility`, `industrial`, `retail`, `telecom`,
`social`, `environment`, `government`, `education`, `scientific`, `synthetic`,
`other`.

Notes: `synthetic` denotes an abstract or generator-native table with no
real-world domain. `other` is used only with a note explaining why no listed
domain fits. Adding a domain term is an additive MINOR benchmark change
(Corpus Protocol Section 7); removing or redefining a term is MAJOR.

## Disposition (FROZEN by the STO register)

`target_leakage`, `structural_constraint`, `redundancy`, `not_applicable`.

## Column role (FROZEN by the STO register, with precedence)

Precedence order (highest first): `target`, `constant`, `identifier`, `datetime`,
`duplicate`, `label_component`, `derived_deterministic`, `leaky_feature`,
`near_deterministic`, `no_signal`, `input`.

## Reserved output symbols (FROZEN)

`STO-X00` (unclassified suspected structure, scored as an abstention),
`ABSTAIN` (explicit abstention on a column set). Support tokens: `<ROWS>`,
`<TABLE>`.

# controlled/

The controlled-generation study: synthetic tables produced from fixed base
tables by a pinned roster of known generators, audited to map generator families
to structural signatures with ground truth.

- `roster.yaml` — the pinned generator roster and seeds.
- `bases/` — the base tables.

At most a small factorial (few bases by few generators). Outputs feed the
Evaluation Corpus `controlled` stratum. Populated in the controlled-generation
work package.

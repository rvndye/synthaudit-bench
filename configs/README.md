# configs/

Human-owned configuration, the base of the layered configuration system
(defaults < file < profile < environment < CLI < per-dataset overrides).

- `default.yaml` — version pins, the determinism seed, and execution limits.
- `thresholds/` — the recommended detector operating points, pinned per STO
  version (populated with the ontology). These are detector defaults, not
  ground truth.
- `corpora/` — census and evaluation corpus settings.
- `profiles/` — named runtime profiles (for example a fast `ci` profile).

Configuration is validated against `schemas/config.schema.json` at load. Version
pins are immutable during a run unless explicitly overridden, and any override is
recorded in the run manifest.

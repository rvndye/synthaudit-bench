# configs/

Human-owned configuration, the file layers of the layered configuration system:

```
packaged defaults < configs/default.yaml < profiles/<p>.yaml
  < environment (SAB_*) < CLI overrides < per-dataset overrides
```

- `default.yaml` — the project's version pins, determinism root seed, and
  execution limits, in the normative config-schema shape.
- `profiles/` — named runtime profiles (for example the fast `ci` profile and the
  generously bounded `full` profile). Profiles override the default layer but MUST
  NOT change version pins without an explicit override.
- `thresholds/` — optional per-STO-version detector operating points. When absent,
  the loader falls back to the operating points shipped as package data
  (`synthaudit_bench/config_data/thresholds/STO-<version>.yaml`). These are
  detector defaults, not ground truth.
- `corpora/` — census and evaluation corpus settings.
- `overrides/` — optional per-dataset override files (`<dataset-id>.yaml`).

Every resolved configuration is validated against the normative `config` schema
at load and fails closed on unknown keys or type errors. Version pins are
immutable during a run unless `--allow-pin-override` is passed, and any override
is recorded in the resolved configuration's provenance and the run manifest. The
resolved values determine the configuration hash used in cache keys and manifests.

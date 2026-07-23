# Instrument pin and verification

SynthAudit-Bench pins the **SynthAudit reference implementation** to a single
version for the entire study, so that the measuring function is constant
(frozen-instrument decision in the Final Blueprint).

- **Pinned version:** `synthaudit==0.1.0`
- **Declared in:** `configs/default.yaml` (`synthaudit_version`) and the
  `synthaudit` optional-dependency extra in `pyproject.toml`.
- **Import boundary:** the core library never imports `synthaudit`; only the
  optional adapter may (enforced by the import-linter contract).

## Verification (reproducible on a fresh clone)

```bash
python -m pip install "synthaudit==0.1.0"
synthaudit selftest --extended --quiet
```

Expected output (the WP0 quality gate):

```json
{ "planted_detected": "11/11", "recall": 1.0, "negative_control_pass": 1.0 }
```

The recorded result of this verification is
`docs/provenance/synthaudit-0.1.0-selftest.json`. At run time the runner also
writes the current instrument self-test into the run manifest
(`results/manifest/`), which is regenerated and therefore not committed.

## Recorded result

Verified 2026-07-23: planted recall `1.0` (11/11) and negative-control pass rate
`1.0`. Gate satisfied.

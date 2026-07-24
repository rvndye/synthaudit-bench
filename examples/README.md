# Examples

Runnable, self-contained examples for SynthAudit-Bench. Each one executes against
the installed package (`pip install -e .` from the repository root) and invents no
behavior beyond the public API and CLI documented under `docs/`.

| Example | What it shows | Run |
|---|---|---|
| `run_pipeline.sh` | End-to-end CLI: `audit → match → report → reproduce` on a tiny synthetic dataset, including report generation | `bash examples/run_pipeline.sh` |
| `plugin_detector.py` | A minimal reference-free detector plugin using the `Detector` protocol (mirrors `docs/detector-protocol.md`) | `python examples/plugin_detector.py` |
| `configuration_demo.py` | Layered configuration resolution and provenance (mirrors `docs/configuration.md`) | `python examples/configuration_demo.py` |

## Quick start

From the repository root, with the package installed:

```bash
bash examples/run_pipeline.sh
```

This creates a temporary dataset with a constant column (STO-S02), a pair of
duplicate columns (STO-A08), and duplicate rows (STO-S01) — the objective classes
the built-in `StructuralBaselineDetector` recovers — then audits it, scores the
audit against gold (detection micro-F1 = 1.0), renders a Markdown report, and
verifies that two runs produce identical hashes.

These examples are illustrative usage, not part of the benchmark's normative
surface; the frozen specification, ontology, schemas, and scoring are unchanged by
anything here.

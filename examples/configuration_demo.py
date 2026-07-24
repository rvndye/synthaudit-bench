"""Layered configuration example (mirrors ``docs/configuration.md``).

Run from the repository root with the package installed::

    python examples/configuration_demo.py

It resolves the full precedence chain (packaged defaults < ``configs/default.yaml``
< profile < environment ``SAB_*`` < CLI overrides < per-dataset overrides), then
prints the effective values, the provenance of one value, and the reproducible
configuration hash. It changes no benchmark semantics; thresholds and limits are
detector configuration only.
"""

from __future__ import annotations

from synthaudit_bench import config


def main() -> None:
    resolved = config.load_config(
        "configs",
        profile="ci",
        env={"SAB_LIMITS__WALL_CLOCK_S": "45"},
        cli_overrides={"jobs": 4},
        dataset_overrides={"limits.memory_mb": 1024},
    )

    source = resolved.provenance.sources["limits.wall_clock_s"]
    print(f"root_seed:    {resolved.config.root_seed}")
    print(f"wall_clock_s: {resolved.config.limits.wall_clock_s} (from {source})")
    print(f"jobs:         {resolved.config.jobs}")
    print(f"config_hash:  {resolved.config_hash()}")
    print(f"layers:       {[layer.kind for layer in config.configuration_layers(resolved)]}")


if __name__ == "__main__":
    main()

# Configuration system

The `synthaudit_bench.config` package resolves a run's configuration from layered
sources into a single immutable, schema-validated value with a reproducible hash
and complete provenance. Every stage of the benchmark is driven by the resolved
configuration, and its hash is recorded in run manifests and used as part of
cache keys, so that a run is defined not only by its inputs but by exactly how it
was configured.

## Configuration lifecycle

A configuration is assembled from ordered layers, merged under a fixed
precedence, checked for forbidden version-pin changes, completed with the pinned
detector thresholds, validated against the normative config schema, and returned
as an immutable `ResolvedConfig`. `load_config` performs the whole lifecycle from
files and the environment; `resolve_config` performs it from layers supplied in
memory, which is what makes resolution testable without touching the filesystem.
The result carries the effective `Config` (the hashable resolved values) and a
`Provenance` record describing how each value was chosen. Nothing is mutated in
place, and no global state is read or written beyond the configuration files and
the injected environment mapping.

## Precedence rules

Layers are resolved lowest to highest precedence:

```
packaged defaults
  < configs/default.yaml
  < profiles/<profile>.yaml
  < environment (SAB_*)
  < CLI overrides
  < per-dataset overrides
```

The packaged defaults are a complete baseline shipped with the library, so a bare
load produces a valid configuration even from an installed wheel with no project
files. `configs/default.yaml` is the project's canonical layer, a named profile
adjusts a run, `SAB_*` environment variables carry non-secret runtime settings, a
CLI layer applies explicit flags, and per-dataset overrides come last. Merging is
deep: a layer that sets `limits.wall_clock_s` leaves `limits.memory_mb` untouched.
Precedence is defined by this declared layer order and never by the order in which
files happen to be discovered on disk. For example, an environment
`SAB_LIMITS__WALL_CLOCK_S=45` overrides a profile's `limits.wall_clock_s`, while a
CLI `jobs` value overrides the same key set by a profile.

## Provenance model

Every resolved value records where it came from. The provenance lists the layers
that participated, in order, and for each one the resolved leaf paths it owns;
maps every dotted key path to the layer that set its final value; names the paths
that more than one layer wrote (the overridden values); and captures the profile,
the threshold version and its source, and the raw environment, CLI, and
per-dataset override mappings that were applied. Provenance is deterministic and
reproducible: the same inputs always produce the same provenance. It is metadata
about the resolution and does not enter the configuration hash, so how a
configuration was assembled is fully auditable without changing the identity of
the values it resolved to.

## Version pin philosophy

Version pins fix the identity of a run: the benchmark version, the STO version,
the schema-set versions, the pinned reference-implementation version, and the
threshold reference. Pins are established by the base layers (the packaged
defaults and `configs/default.yaml`) and are immutable for the rest of the
resolution. A profile, an environment variable, a CLI flag, or a per-dataset
override that tries to change a pin fails closed with a `PinOverrideError`, so a
run cannot silently drift off its pinned identity. When a change is genuinely
intended, passing `allow_pin_override` permits it and records the event in
provenance, capturing the path, the previous and new values, and the layer that
made the change, so the override is visible in the run manifest and outputs.

## Threshold management

Detector operating points (specification Appendix D) are loaded from a YAML file
pinned per STO version, either `configs/thresholds/STO-<version>.yaml` in the
project or the operating points shipped as package data when the project does not
override them. Thresholds are detector defaults only. They are not ground truth:
changing a threshold changes a detector's behavior, but it never changes the
benchmark semantics or the gold labels. Because the resolved thresholds are part
of the configuration values, any change to them changes the configuration hash
and is therefore auditable, while leaving everything the thresholds do not govern
exactly as it was.

## Reproducibility guarantees

Resolution is deterministic: given the same layers, environment, and overrides,
it produces byte-identical resolved values and therefore an identical
configuration hash. The hash is the content address of the effective `Config`
(canonical JSON, SHA-256), so it is stable across machines and processes and is
independent of dictionary insertion order or file-discovery order. The resolved
configuration is validated against the normative config schema and fails closed
on unknown keys or type errors, so an invalid configuration can never be hashed
or run. Together these make a configuration a first-class, verifiable part of a
run's identity.

## Examples

A bare load uses the packaged defaults, and a project load layers files and
overrides on top:

```python
from synthaudit_bench import config

resolved = config.load_config()                 # packaged defaults only
resolved.config.root_seed                        # 42
resolved.config_hash()                           # stable content address

resolved = config.load_config(
    "configs",
    profile="ci",
    env={"SAB_LIMITS__WALL_CLOCK_S": "45"},
    cli_overrides={"jobs": 4},
    dataset_overrides={"limits.memory_mb": 1024},
)
resolved.config.limits.wall_clock_s              # 45  (environment beats the profile)
resolved.config.jobs                             # 4   (CLI)
resolved.provenance.sources["limits.wall_clock_s"]   # "environment"
[layer.kind for layer in config.configuration_layers(resolved)]
# ["packaged", "default", "profile", "environment", "cli", "dataset"]
```

Version pins are immutable unless explicitly overridden:

```python
config.load_config("configs", cli_overrides={"pins.sto_version": "2.0.0"})
# raises PinOverrideError

resolved = config.load_config(
    "configs", cli_overrides={"pins.bench_version": "1.1.0"}, allow_pin_override=True
)
resolved.provenance.pin_overrides[0]
# PinOverride(path="pins.bench_version", previous="1.0.0", new="1.1.0", layer="cli")
```

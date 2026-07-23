"""The layered configuration subsystem (architecture Section 8).

Resolves configuration from the fixed precedence chain (packaged defaults <
``configs/default.yaml`` < profile < environment ``SAB_*`` < CLI < per-dataset
overrides) into an immutable, schema-validated :class:`ResolvedConfig` that
records the complete provenance of every value and a reproducible configuration
hash. Version pins are immutable during resolution unless explicitly overridden,
and detector thresholds are loaded as pinned operating defaults that change the
configuration hash but never the benchmark semantics or gold labels.
"""

from __future__ import annotations

from synthaudit_bench.config.errors import (
    ConfigError,
    PinOverrideError,
    UnknownProfileError,
)
from synthaudit_bench.config.loader import (
    expand_dotted,
    load_profile,
    load_thresholds,
    packaged_defaults,
    parse_env,
)
from synthaudit_bench.config.provenance import (
    LayerContribution,
    PinOverride,
    Provenance,
    ResolvedConfig,
)
from synthaudit_bench.config.resolver import (
    ConfigLayer,
    config_hash,
    configuration_layers,
    effective_configuration,
    load_config,
    resolve_config,
)

__all__ = [
    "ConfigError",
    "ConfigLayer",
    "LayerContribution",
    "PinOverride",
    "PinOverrideError",
    "Provenance",
    "ResolvedConfig",
    "UnknownProfileError",
    "config_hash",
    "configuration_layers",
    "effective_configuration",
    "expand_dotted",
    "load_config",
    "load_profile",
    "load_thresholds",
    "packaged_defaults",
    "parse_env",
    "resolve_config",
]

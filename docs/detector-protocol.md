# Detector protocol and normalization

The `synthaudit_bench.detector` package is the tool-agnostic seam of the
benchmark: the stable interface any structural auditing system implements to be
scored, and the pipeline that turns a detector's raw output into canonical,
schema-valid artifact tuples. The benchmark is a task, not a tool (specification
Section 1.2), so the core never imports a specific detector; detectors are
discovered through an entry-point group, and the reference SynthAudit adapter (an
optional extra, the only component that imports the reference implementation) uses
exactly this public protocol.

## The detector protocol

A detector implements two methods. `capabilities()` returns an immutable
`DetectorCapabilities` declaration, and `detect(dataset, context)` evaluates a
dataset and emits raw findings. `detect` must be reference-free (it reads only the
dataset it is given, never the network or an external model; Section 5.1),
deterministic given the dataset and `context.seed` (Section 5.8), and it must
never mutate the dataset or any benchmark state. It may raise: the runner isolates
the failure. Objective-class detection must use the full non-missing data.

The protocol has no heavy dependencies, so a third-party detector can implement it
without importing the benchmark's internals. Two optional lifecycle hooks are
honored when present: `setup(context)` for initialization and configuration
injection, and `teardown()` for graceful shutdown. The convenience base
`BaseDetector` supplies no-op hooks so a detector only has to define `capabilities`
and `detect`, but subclassing is not required.

## The capability model

`DetectorCapabilities` is how a detector advertises what it can do: the supported
STO categories (group letters like `A` or specific class ids), the dataset
modalities and logical types it accepts, the benchmark and (optionally) ontology
versions it requires, its name and version, its reference-free flag, and any
optional or experimental capabilities. `detector_capabilities` and
`detector_metadata` read this declaration; the latter is the compact identity and
version report that goes into a run manifest.

Capability negotiation happens before execution. `capability_issues` returns every
reason a detector is incompatible with a run (a required version the run cannot
offer, an unsupported modality or logical type) without raising, and
`validate_detector` is the raising pre-flight gate built on it. `run_detector`
performs the same check internally and records a structured error rather than
raising, so an incompatible detector never crashes a batch.

## Execution and isolation

`run_detector` is the task boundary, and it never raises. It declares and
validates capabilities, honors the below-minimum rule (an empty result plus a
`below_minimum` note for a table under 200 rows or 4 columns, Section 5.9 E-2),
runs the detector under the optional `context.timeout_s` budget, confirms the
detector did not mutate the immutable dataset (a changed content hash is a runtime
failure), and normalizes the findings. Every failure, a capability mismatch, a
timeout (recorded as a `resource` failure, E-4), a detector exception (a `runtime`
failure), or a malformed finding (an `invalid_findings` failure), becomes a
structured `ErrorRecord` on the `AuditResult`. This is what makes one detector's
failure isolated: it is turned into a record and the batch continues.

A timeout is detected by running the detector in a worker and abandoning it if it
overruns; hard cancellation of a runaway detector is the batch runner's
process-pool job (a later work package), while this layer detects and records the
breach deterministically.

## The normalization pipeline

`normalize_findings` turns raw findings into canonical `ArtifactTuple`s
(Section 5.3). For each finding it resolves the native identifier to an STO class,
canonicalizes the support (a reserved `<ROWS>`/`<TABLE>` token or the unordered set
of participating columns), takes the disposition from the finding or infers it when
decidable, normalizes confidence and severity, validates the evidence, collapses
duplicate tuples (identical support, class, and disposition) to one, orders the
result deterministically by `(class, support, disposition)`, and validates every
tuple against the normative tuple schema. Normalization is pure: the same findings,
dataset, mapper, and ontology version always produce the same ordered tuples, and
a malformed finding fails closed with a structured error.

Disposition inference follows Section 4.3. With no target, or for a target-independent
class (the S group and STO-R02), the disposition is `not_applicable`. Otherwise it is
`target_leakage` when the target is in the support, `redundancy` for a duplicate
column (STO-A08) among non-target columns, and `structural_constraint` for any other
relation among non-target columns. When the target relationship cannot be decided from
the support alone (a whole-row token), the disposition is left for the detector to
declare.

## Ontology mapping

`map_to_ontology` and `OntologyMapper` resolve a detector's native vocabulary into
STO identifiers, following the frozen ontology: exact mappings, aliases for
alternate spellings, automatic resolution of a deprecated class to its
replacement, and binding to a specific ontology version. A mapping table is
validated when it is built, so a table that targets an identifier which is not a
known STO class fails closed. Any identifier that resolves to no known class
becomes `STO-X00` (unclassified), which the benchmark scores as an abstention and
never as a false positive (Sections 5.9 E-3, 4.1 P4).

## The confidence model

An artifact tuple's confidence is an optional real in `[0, 1]`.
`normalize_confidence` turns a detector-native or calibrated value into that
canonical range, treats an unavailable value as `None` (the tuple omits the
field), and raises a structured error for anything that is not a finite number in
range; a non-strict mode clamps instead of raising. Normalization never invents a
value.

## Extending: a minimal detector plugin

A detector is any object with `capabilities` and `detect`. This one flags constant
columns (STO-S02), depending only on the public interface and the immutable
dataset:

```python
from collections.abc import Iterable

from synthaudit_bench.detector import (
    BaseDetector, DetectorCapabilities, ExecutionContext, RawFinding,
)
from synthaudit_bench.model.dataset import DatasetObject


class ConstantColumnDetector(BaseDetector):
    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(
            name="constant-column", version="1.0.0",
            required_bench_version="1.0.0", sto_categories=frozenset({"S"}),
        )

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Iterable[RawFinding]:
        for column in dataset.columns:
            if dataset.table[column].nunique(dropna=True) <= 1:
                yield RawFinding(identifier="STO-S02", support=(column,), severity="low")
```

Run it directly, or register and discover it:

```python
from synthaudit_bench.detector import (
    ExecutionContext, register_detector, run_detector,
)

registry = register_detector("constant-column", ConstantColumnDetector)
detector = registry.create("constant-column")
result = run_detector(detector, dataset, ExecutionContext())
```

To ship a detector as an installable plugin, declare it under the
`synthaudit_bench.detectors` entry-point group in the plugin's own `pyproject.toml`;
`discover_detectors()` finds every installed detector, loading each independently so
a broken or heavy optional plugin is recorded and skipped rather than breaking the
others. Registration and discovery return immutable registry values, so there is no
mutable global anywhere.

## Public API

Protocol and model: `Detector`, `BaseDetector`, `DetectorCapabilities`,
`ExecutionContext`, `RawFinding`, `DetectionResult`, `DetectorMetadata`.
Registration and discovery: `register_detector`, `discover_detectors`,
`DetectorRegistry`. Execution: `run_detector`, `validate_detector`. Normalization:
`normalize_findings`, `map_to_ontology`, `build_ontology_mapper`,
`normalize_confidence`, `detector_capabilities`, `detector_metadata`. Every
function is deterministic, reads only its inputs, and (outside a detector's own
`detect`) performs no external access.

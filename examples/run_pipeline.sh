#!/usr/bin/env bash
# End-to-end CLI example: audit -> match -> report -> reproduce, on a tiny
# synthetic dataset. Requires the package installed so the `bench` console script
# is on PATH (`pip install -e .` from the repository root).
#
# Run from the repository root:
#     bash examples/run_pipeline.sh
set -euo pipefail

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# 1. A tiny dataset carrying the objective artifacts the built-in baseline detects:
#    a constant column (STO-S02), a duplicate column pair (STO-A08), and duplicate
#    rows (STO-S01).
python - "$work/data.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], "w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["k", "b", "c", "g"])
    writer.writeheader()
    for i in range(250):
        writer.writerow({"k": "1", "b": str(i % 4), "c": str(i % 4), "g": str(i % 2)})
PY

# 2. Gold tuples for the dataset, authored through the domain model so the file is
#    schema-valid (gold authoring is a corpus-maintainer task, shown here for a
#    self-contained scoring example).
mkdir -p "$work/gold"
python - "$work/gold/data.json" <<'PY'
import json
import sys

from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ROWS, GoldTuple

gold = [
    GoldTuple(frozenset({"k"}), frozenset({"STO-S02"}),
              frozenset({Disposition.NOT_APPLICABLE}), GoldType.OBJECTIVE,
              evidence="constant column"),
    GoldTuple(frozenset({"b", "c"}), frozenset({"STO-A08"}),
              frozenset({Disposition.REDUNDANCY}), GoldType.OBJECTIVE,
              evidence="duplicate columns"),
    GoldTuple(ROWS, frozenset({"STO-S01"}),
              frozenset({Disposition.NOT_APPLICABLE}), GoldType.OBJECTIVE,
              evidence="duplicate rows"),
]
with open(sys.argv[1], "w") as handle:
    json.dump([tuple_.to_mapping() for tuple_ in gold], handle)
PY

echo "== bench audit =="
bench audit "$work/data.csv" --target g --split public-dev --out "$work/out"

echo "== bench match (score the audit against gold) =="
bench match --audits "$work/out/audits" --gold "$work/gold" --split public-dev

echo "== bench report (render a Markdown report) =="
bench report --audits "$work/out/audits" --format md

echo "== bench reproduce (two runs, identical hashes) =="
bench reproduce "$work/data.csv" --target g

echo "== done =="

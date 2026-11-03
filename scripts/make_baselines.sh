#!/usr/bin/env bash
# Regenerates tests/baselines/ (output of `dbt compile`) and re-vendors dbt's global macros.
# Needs uv (https://docs.astral.sh/uv/) and network (pip) but NO database: compile runs with --no-populate-cache.
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv -q --clear --python 3.12 .baseline-venv
uv pip install -q --python .baseline-venv/bin/python -r scripts/baseline-requirements.txt
.baseline-venv/bin/python scripts/make_baselines.py

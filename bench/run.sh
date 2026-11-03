#!/usr/bin/env bash
# Reproduces the README "Comparison" table: the same 5 macro checks done three ways.
# Needs: uv (https://docs.astral.sh/uv/), network (PyPI), Python 3.12. No database server; (c) writes a local DuckDB file.
# Usage: bench/run.sh            (work dir: bench/.work, override with WORK=...; runs per method: RUNS=3)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$HERE/.."
WORK="${WORK:-$HERE/.work}"; RUNS="${RUNS:-3}"
rm -rf "$WORK"; mkdir -p "$WORK"
echo "env: $(uname -sr) | $(sysctl -n machdep.cpu.brand_string 2>/dev/null || grep -m1 'model name' /proc/cpuinfo) | $(date +%F)"

# dbt-utils 1.4.1 copy (Apache-2.0) already vendored as a test fixture; (b) and (c) install it with `dbt deps` (local path)
cp -R "$ROOT/tests/fixtures/project/dbt_packages/dbt_utils" "$WORK/dbt_utils_src"

setup() {  # name, pip packages...
  local n=$1; shift
  uv venv -q --python 3.12 "$WORK/$n.venv"
  uv pip install -q --python "$WORK/$n.venv/bin/python" "$@"
  cp -R "$HERE/$n" "$WORK/$n"
}
M="python3 $HERE/measure.py"

setup a_pytest_dbt_macros pytest "$ROOT"
cp -R "$ROOT/tests/fixtures/project/dbt_packages" "$WORK/a_pytest_dbt_macros/"
PATH="$WORK/a_pytest_dbt_macros.venv/bin:$PATH" bash -c "cd $WORK/a_pytest_dbt_macros && python -m pytest -q"
$M a "$WORK/a_pytest_dbt_macros.venv" "$WORK/a_pytest_dbt_macros" "$RUNS" -- python -m pytest -q test_macros.py
echo "multi-target (a): $(cd "$WORK/a_pytest_dbt_macros" && ../a_pytest_dbt_macros.venv/bin/python -m pytest -q test_multi_target.py | tail -1)"

setup b_pytest_dbt_core pytest pytest-dbt-core dbt-duckdb
B="$WORK/b_pytest_dbt_core"
(cd "$B" && ../b_pytest_dbt_core.venv/bin/dbt deps --profiles-dir . >/dev/null && ../b_pytest_dbt_core.venv/bin/python -m pytest -q --profiles-dir .)
$M b "$B.venv" "$B" "$RUNS" -- python -m pytest -q --profiles-dir .
echo "multi-target (b), second target in a second process: $(cd "$B" && ../b_pytest_dbt_core.venv/bin/python -m pytest -q --profiles-dir . --dbt-target duckdb2 | tail -1)"

setup c_dbt_unit_tests dbt-duckdb
C="$WORK/c_dbt_unit_tests"
(cd "$C" && ../c_dbt_unit_tests.venv/bin/dbt deps --profiles-dir . >/dev/null && ../c_dbt_unit_tests.venv/bin/dbt build --profiles-dir . | tail -3)
$M c "$C.venv" "$C" "$RUNS" -- dbt build --profiles-dir .
echo "multi-target (c), second target in a second invocation: $(cd "$C" && ../c_dbt_unit_tests.venv/bin/dbt build --profiles-dir . --target duckdb2 | tail -1)"

echo "versions:"; for n in a_pytest_dbt_macros b_pytest_dbt_core c_dbt_unit_tests; do
  uv pip freeze --python "$WORK/$n.venv/bin/python" | grep -iE '^(dbt-core|dbt-duckdb|pytest-dbt|pytest)==|^pytest.dbt' | tr '\n' ' '; echo; done
echo "test lines (wc -l):"; wc -l "$HERE"/a_*/test_macros.py "$HERE"/b_*/test_macros.py "$HERE"/c_*/models/*.sql "$HERE"/c_*/models/unit_tests.yml

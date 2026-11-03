# pytest-dbt-macros

Unit-test dbt macros (Jinja) with pytest, **without dbt-core, an adapter, `profiles.yml` or a database**.

> This is an open-source experiment built by AI agents at start-up-team-k. It is v0.1: expect rough edges, and
> issues and feedback are welcome.

## Why

Shared dbt macros grow, branch per warehouse (`adapter.dispatch`), and are hard to test. dbt's built-in unit tests
cover SQL models only ([dbt-labs/dbt#10547](https://github.com/dbt-labs/dbt/issues/10547) asks for macro tests).
[pytest-dbt-core](https://github.com/godatadriven/pytest-dbt-core) tests macros with pytest but builds on dbt-core,
an adapter package and a profile. This plugin instead re-implements the small part of dbt's Jinja context that macros
need (`ref`, `var`, `target`, `adapter.dispatch`, ...), so a test is: load macros, call, compare SQL strings.
The same approach is used by [SQLFluff's Jinja templater](https://docs.sqlfluff.com/en/stable/configuration/templating/jinja.html)
(Apache/MIT-style mocks); here it is packaged for pytest and checked against real `dbt compile` output.

## Install

On PyPI: https://pypi.org/project/pytest-dbt-macros/ . Python >= 3.10. Examples: [`examples/`](examples/) (dbt-utils multi-target project, GitHub Actions workflow). Docs page: https://start-up-team-k.github.io/pytest-dbt-macros/ .

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install pytest-dbt-macros
```

Runtime dependencies: `jinja2`, `pyyaml`, `pytest`, `sqlglot`. dbt-core is **not** installed or imported.

## Quick start

Create a tiny dbt-style project (or use your existing one: run pytest from the folder that has `dbt_project.yml`):

```bash
mkdir demo && cd demo && mkdir macros
printf 'name: demo\n' > dbt_project.yml
cat > macros/money.sql <<'SQL'
{% macro cents_to_dollars(col) -%}
    {{ return(adapter.dispatch('cents_to_dollars')(col)) }}
{%- endmacro %}

{% macro default__cents_to_dollars(col) -%}
    ({{ col }} / 100.0)
{%- endmacro %}

{% macro bigquery__cents_to_dollars(col) -%}
    safe_divide({{ col }}, 100)
{%- endmacro %}

{% macro require_col(col) -%}
    {%- if not col -%}{{ exceptions.raise_compiler_error("col is required") }}{%- endif -%}
    {{ col }}
{%- endmacro %}
SQL
cat > test_money.py <<'PY'
import pytest
from pytest_dbt_macros import CompilationError, assert_sql_equal


def test_default(dbt_macros):
    assert_sql_equal(dbt_macros.cents_to_dollars("amount"), "(amount / 100.0)")


def test_bigquery_branch(dbt_macros):
    dbt_macros.target["type"] = "bigquery"      # what `target.type` returns inside the macros
    assert_sql_equal(dbt_macros.cents_to_dollars("amount"), "safe_divide(amount, 100)")


def test_dbt_global_macro(dbt_macros):          # dbt.concat etc. are bundled
    assert_sql_equal(dbt_macros.render("{{ dbt.concat(['a', 'b']) }}"), "a || b")


def test_error(dbt_macros):
    with pytest.raises(CompilationError, match="col is required"):
        dbt_macros.require_col("")
PY
pytest -v
```

The `dbt_macros` fixture loads, for the project in the current directory: its `macros/` folders (`macro-paths`),
every package in `dbt_packages/` (so `dbt_macros.dbt_utils.generate_surrogate_key(["a", "b"])` works after `dbt deps`),
and dbt's own cross-database macros (`dbt.concat`, `dbt.hash`, `dbt.type_string`, `dbt.dateadd`, ...).
Calling a macro returns its rendered text (or the value passed to `return(...)`).

- `dbt_macros.<macro>(...)`, `dbt_macros.<package>.<macro>(...)`, `dbt_macros.render("{{ ... }}")`
- `dbt_macros.target["type"]` / `.vars` / `.env`: change `target.type`, `var()`, `env_var()` at any time.
- `dispatch:` in `dbt_project.yml` is honoured (`macro_namespace`, `search_order`), and so is dbt's lookup order
  `<adapter>__name` -> parent adapter (`redshift` -> `postgres`) -> `default__name`.
- `assert_sql_equal(actual, expected, dialect=None)` compares after sqlglot normalization (whitespace, keyword and
  identifier case). If sqlglot cannot parse a fragment, it falls back to whitespace-insensitive comparison.
- To point at another folder, override the `dbt_project_dir` fixture in `conftest.py`.

## Test

```bash
git clone https://github.com/start-up-team-k/pytest-dbt-macros && cd pytest-dbt-macros
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest
pytest
```

`tests/test_baselines.py` renders 17 cases (dbt-utils 1.4.1 macros, dbt global macros, project macros and a
`dispatch:` override) for four `target.type`s (postgres, snowflake, bigquery, duckdb) and compares each with the SQL that
`dbt compile` produced (stored in `tests/baselines/<target>/`). Versions used: see `tests/baselines/VERSIONS.txt`
(dbt-core 1.12.6, dbt-postgres 1.11.0, dbt-snowflake 1.12.4, dbt-bigquery 1.12.1, dbt-duckdb 1.11.1, dbt-utils 1.4.1).
To regenerate (needs [uv](https://docs.astral.sh/uv/) and network, no database): `scripts/make_baselines.sh`.

## How dbt's built-in macros are handled

dbt-utils calls `dbt.concat`, `dbt.hash`, `dbt.dateadd`, ... which live in dbt-adapters and the adapter packages.
Instead of importing them (which would need dbt-core), the plugin **bundles unmodified copies** of the `macros/utils/`
folders (plus `timestamps.sql`) of dbt-adapters 1.24.5, dbt-postgres 1.11.0, dbt-snowflake 1.12.4, dbt-bigquery 1.12.1
and dbt-duckdb 1.11.1 (all Apache-2.0) in `src/pytest_dbt_macros/vendored/`. Each folder keeps its upstream LICENSE;
see `NOTICE`. Other adapters fall back to `default__` macros, which may not match what that adapter really does.

## Comparison

The same five checks (`dbt_utils.generate_surrogate_key`, `dbt_utils.deduplicate`, `dbt_utils.haversine_distance`,
`dbt.dateadd`, `dbt.datediff`; dbt-utils 1.4.1, `target.type` = duckdb) written three ways. Everything is in
[`bench/`](bench/) and reproduced by [`bench/run.sh`](bench/run.sh) (needs `uv` and network, no database server).
Measured 2026-11-03 on macOS (Darwin 25.6.0), Apple M4, Python 3.12, fresh uv venvs, dbt-core 1.12.6, dbt-duckdb 1.11.1.

| | (a) pytest-dbt-macros | (b) pytest-dbt-core 0.2.4 + dbt-duckdb | (c) dbt unit tests (dummy models) + dbt-duckdb |
|---|---|---|---|
| Packages installed (`uv pip freeze` lines) | 12 | 64 | 59 |
| `site-packages` size | 17.9 MB | 166.0 MB | 157.4 MB |
| Config files you write | 1 (`dbt_project.yml`) | 3 (`dbt_project.yml`, `profiles.yml`, `packages.yml`) | 4 (same three + `unit_tests.yml`), plus 7 dummy model `.sql` files |
| Test code lines | 38 | 42 | 51 (38 YAML + 13 SQL) |
| Wall time, mean of 3 runs (whole process) | 0.214 s | 1.149 s | 2.395 s |
| Several `target.type` in one run | yes: `dbt_macros.target["type"] = ...` per test (3 targets in `bench/a_pytest_dbt_macros/test_multi_target.py`) | no: one `--dbt-target` per pytest process; each non-DuckDB type needs its adapter package and a profile it can connect with | no: one `--target` per `dbt build`; same adapter requirement |
| What is checked | rendered SQL string | rendered SQL string | result of executing the SQL on DuckDB |

Notes (facts only):
- (b) works with the latest dbt-core (1.12.6) and Python 3.12; 5/5 pass. It needs `--profiles-dir` (without it
  pytest-dbt-core 0.2.4 raises `TypeError: expected str, bytes or os.PathLike object, not NoneType`), and it does not
  install `pytest` itself. Its last release is 2024-06-04.
- The dbt-based setups need `dbt deps` once (not timed). (c) also builds the dummy views in a DuckDB file on each run.
- Times include interpreter start-up and imports; the first (untimed) run per setup warms bytecode caches.
  (a)/(b) timings run only the five-check file; (c) runs `dbt build` (7 views + 5 unit tests).
- (b)/(c) were not tried on non-DuckDB adapters: their fixtures/commands open a connection to the warehouse.
- Compare with real warehouses: only (c) runs SQL; (a) and (b) compare strings. Raw numbers: `bench/run.sh` output.

## Scope

Does:
- Render macros from your project and from installed packages to SQL strings, call them from Python.
- Stubs: `ref`, `source`, `var`, `env_var`, `target`, `config`, `log`, `return`, `exceptions.*`, `adapter.dispatch/type/quote`,
  `api.Column.translate_type/numeric_type`, `modules`, `execute`, `dbt_version`.
- Declare a relation's columns, e.g. `dbt_macros.columns["users"] = ["id", "name"]`; then `ref('users')` works with
  `adapter.get_columns_in_relation` and `dbt_utils.star(ref('users'))` renders (checked against `dbt compile` output on DuckDB
  in `tests/test_star.py`). Names only: no column types.
- Check cross-database branches by switching `target.type`; assert expected errors with `pytest.raises(CompilationError)`.

Does not (yet):
- Run the SQL: no DuckDB execution of rendered SQL (planned, not implemented).
- Anything that needs a database: `run_query`, `statement`, `get_column_values`, `date_spine`. `union_relations` also
  fails (needs column types). Columns can be declared by hand for `adapter.get_columns_in_relation` (see below).
- Models, materializations, hooks, `{% test %}` blocks (parsed and ignored), snapshots, docs blocks.
- Quoted, fully-qualified relations: `ref('x')` renders as `x`, `source('s', 't')` as `s.t`.
- dbt Fusion.

## Limitations

- Fidelity: this is a re-implementation of dbt's Jinja context, not dbt. Known differences: relations render unquoted and
  without database/schema; only the context names listed above exist (no `this`, `model`, `graph`, `flags`,
  `modules.pytz`, ...), so macros using them fail with an `UndefinedError`; `var()` scoping is simplified (project-level
  `vars:` plus `vars=` you pass; no `--vars` or package-scoped lookups beyond the root project's own); `adapter.behavior`
  flags are not available; `target` has only `type`, `name`, `schema`, `database`, `threads`.
- Baselines cover 17 cases on 4 targets compared against dbt-core 1.12.6 only. Other dbt versions or macros may differ.
- The bundled dbt macros are pinned to the versions above and are not updated automatically.
- Some dbt global macros are implemented in Python by an adapter rather than in SQL, so the bundle has no version of
  them. Example: `dbt.current_timestamp()` with `target.type = "duckdb"` fails with "not implemented for adapter duckdb"
  ([#1](https://github.com/start-up-team-k/pytest-dbt-macros/issues/1)).

## License

MIT (see `LICENSE`). Bundled third-party files are Apache-2.0 (see `NOTICE`).

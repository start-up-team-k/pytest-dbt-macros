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

PyPI is not published yet. Python >= 3.10.

```bash
python -m venv .venv && . .venv/bin/activate
pip install pytest git+https://github.com/start-up-team-k/pytest-dbt-macros
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
python -m venv .venv && . .venv/bin/activate
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

## Scope

Does:
- Render macros from your project and from installed packages to SQL strings, call them from Python.
- Stubs: `ref`, `source`, `var`, `env_var`, `target`, `config`, `log`, `return`, `exceptions.*`, `adapter.dispatch/type/quote`,
  `api.Column.translate_type/numeric_type`, `modules`, `execute`, `dbt_version`.
- Check cross-database branches by switching `target.type`; assert expected errors with `pytest.raises(CompilationError)`.

Does not (yet):
- Run the SQL: no DuckDB execution of rendered SQL (planned, not implemented).
- Anything that needs a database: `run_query`, `statement`, `adapter.get_columns_in_relation` (so `dbt_utils.star`,
  `get_column_values`, `date_spine`, `union_relations` fail with an error; for `star` and `union_relations` the message
  is a misleading "expected a Relation", because `ref()` returns a plain string, not a dbt Relation object).
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
- Not on PyPI yet; install from GitHub.

## License

MIT (see `LICENSE`). Bundled third-party files are Apache-2.0 (see `NOTICE`).

# Changelog

An open-source experiment built by AI agents (start-up-team-k).

## Unreleased
- Rename the PyPI release workflow file to `workflow.yml` (manual `workflow_dispatch` only; nothing is published yet).
- Add `examples/` (dbt-utils multi-target project, minimal GitHub Actions workflow), issue templates, a docs page
  (GitHub Pages), package keywords and URLs.

## 0.2.0
- `dbt_macros.columns["users"] = [...]` declares a relation's columns; `dbt_utils.star` now renders (checked against `dbt compile` on DuckDB).
- `bench/`: comparison with pytest-dbt-core and dbt unit tests.

## 0.1.0
- First release: `dbt_macros` pytest fixture, dbt context stubs, `adapter.dispatch`, bundled dbt global macros
  (postgres, snowflake, bigquery, duckdb), `assert_sql_equal`, baselines checked against `dbt compile`.

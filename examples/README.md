# Examples

Part of an open-source experiment built by AI agents (start-up-team-k). Copy what is useful.

## `dbt_utils_multi_target/`

A small dbt project whose macros wrap `dbt_utils.generate_surrogate_key` and branch with `adapter.dispatch`.
`test_shop.py` checks the SQL for postgres, snowflake and bigquery in one pytest run by changing `target.type`.

```bash
cd examples/dbt_utils_multi_target
git clone --depth 1 --branch 1.4.1 https://github.com/dbt-labs/dbt-utils dbt_packages/dbt_utils   # what `dbt deps` would fetch
pytest -v
```

`dbt_packages/` is git-ignored; the clone replaces `dbt deps` so dbt-core is not needed. Expected SQL strings were
produced with dbt-utils 1.4.1 and match the baselines in `tests/baselines/`.

## `github-actions/test-macros.yml`

Minimal GitHub Actions workflow that runs only macro tests. The `examples` job in this repo's CI runs the same steps
against the example project above.

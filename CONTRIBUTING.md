# Contributing

This project is an experiment by AI agents at start-up-team-k; humans are very welcome to file issues and PRs.

- Dev setup: `python3 -m venv .venv && . .venv/bin/activate && pip install -e . pytest && pytest`
- A bug where a rendered macro differs from `dbt compile` is the most valuable kind of report. Please include the macro, the `target.type`, and the dbt output. To add a regression case, put the Jinja in `tests/baselines/cases.json` and run `scripts/make_baselines.sh` (needs `uv`; no database needed), then commit the regenerated baselines.
- Keep the runtime free of dbt-core and keep the code small. Anything that needs a database connection is out of scope.
- `src/pytest_dbt_macros/vendored/` and `tests/fixtures/project/dbt_packages/` are third-party Apache-2.0 files; do not edit them by hand (see `NOTICE`).

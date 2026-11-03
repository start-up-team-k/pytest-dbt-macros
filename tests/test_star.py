"""dbt_utils.star needs a column list; `dbt_macros.columns` supplies it (no database).
Expected files come from `dbt compile` on DuckDB after `dbt run` created the table (scripts/make_baselines.py)."""
from pathlib import Path

import pytest

from pytest_dbt_macros import CompilationError, assert_sql_equal

BASE = Path(__file__).parent / "baselines_star"


@pytest.mark.parametrize("name,call", [
    ("star_all", "dbt_utils.star(ref('users'))"),
    ("star_except_prefix", "dbt_utils.star(ref('users'), except=['email'], prefix='u_')"),
])
def test_star_matches_dbt_compile(dbt_macros, name, call):
    dbt_macros.target["type"] = "duckdb"
    dbt_macros.columns["users"] = ["id", "name", "email"]
    assert_sql_equal(dbt_macros.render("{{ %s }}" % call), (BASE / f"{name}.sql").read_text())


def test_star_without_declared_columns(dbt_macros):
    with pytest.raises(CompilationError, match="dbt_macros.columns"):
        dbt_macros.render("{{ dbt_utils.star(ref('users')) }}")

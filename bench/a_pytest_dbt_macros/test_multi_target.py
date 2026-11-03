import pytest
from pytest_dbt_macros import assert_sql_equal

EXPECTED = {  # one test, several target.type values, one pytest process
    "duckdb": "(order_date + cast(7 as bigint) * interval 1 day)",
    "postgres": "order_date + ((interval '1 day') * (7))",
    "bigquery": "datetime_add(cast( order_date as datetime), interval 7 day)",
}


@pytest.mark.parametrize("target", EXPECTED)
def test_dateadd_per_target(dbt_macros, target):
    dbt_macros.target["type"] = target
    assert_sql_equal(dbt_macros.dbt.dateadd("day", 7, "order_date"), EXPECTED[target],
                     dialect=None if target == "duckdb" else target)

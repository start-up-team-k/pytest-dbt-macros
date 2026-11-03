import pytest
from pytest_dbt_macros import assert_sql_equal

KEY = ("{h}(cast(coalesce(cast(customer_id as {t}), '_dbt_utils_surrogate_key_null_') || '-' || "
       "coalesce(cast(order_id as {t}), '_dbt_utils_surrogate_key_null_') as {t}))")
EXPECTED_KEY = {  # dbt_utils.generate_surrogate_key differs per warehouse
    "postgres": KEY.format(h="md5", t="TEXT"),
    "snowflake": KEY.format(h="md5", t="TEXT"),
    "bigquery": "to_hex(" + KEY.format(h="md5", t="string") + ")",
}


@pytest.mark.parametrize("target", EXPECTED_KEY)
def test_order_key_per_target(dbt_macros, target):
    dbt_macros.target["type"] = target          # what target.type returns inside the macros
    assert_sql_equal(dbt_macros.order_key("customer_id", "order_id"), EXPECTED_KEY[target], dialect=target)


def test_days_since_bigquery_branch(dbt_macros):  # <adapter>__days_since wins on bigquery
    dbt_macros.target["type"] = "bigquery"
    assert_sql_equal(dbt_macros.days_since("created_at"),
                     "date_diff(current_date(), date(created_at), day)", dialect="bigquery")


def test_days_since_default_branch(dbt_macros):   # everything else uses default__days_since
    dbt_macros.target["type"] = "postgres"
    assert_sql_equal(dbt_macros.days_since("created_at"), "((now())::date - (created_at)::date)", dialect="postgres")

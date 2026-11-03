from pytest_dbt_macros import assert_sql_equal


def test_surrogate_key(dbt_macros):
    dbt_macros.target["type"] = "duckdb"
    assert_sql_equal(
        dbt_macros.dbt_utils.generate_surrogate_key(["order_id", "customer_id"]),
        "md5(cast(coalesce(cast(order_id as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || "
        "coalesce(cast(customer_id as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT))")


def test_deduplicate(dbt_macros):
    dbt_macros.target["type"] = "duckdb"
    assert_sql_equal(
        dbt_macros.dbt_utils.deduplicate("my_table", "user_id", "updated_at desc"),
        """with row_numbered as (select _inner.*, row_number() over (partition by user_id
        order by updated_at desc) as rn from my_table as _inner)
        select distinct data.* from my_table as data natural join row_numbered where row_numbered.rn = 1""")


def test_dateadd(dbt_macros):
    dbt_macros.target["type"] = "duckdb"
    assert_sql_equal(dbt_macros.dbt.dateadd("day", 7, "order_date"),
                     "(order_date + cast(7 as bigint) * interval 1 day)")


def test_datediff(dbt_macros):
    dbt_macros.target["type"] = "duckdb"
    assert_sql_equal(dbt_macros.dbt.datediff("start_ts", "end_ts", "hour"),
                     "(date_diff('hour', start_ts::timestamp, end_ts::timestamp))")


def test_haversine(dbt_macros):
    dbt_macros.target["type"] = "duckdb"
    assert_sql_equal(
        dbt_macros.dbt_utils.haversine_distance("lat1", "lon1", "lat2", "lon2"),
        "2 * 3961 * asin(sqrt(power((sin(radians((lat2 - lat1) / 2))), 2) + cos(radians(lat1)) * "
        "cos(radians(lat2)) * power((sin(radians((lon2 - lon1) / 2))), 2))) * 1")

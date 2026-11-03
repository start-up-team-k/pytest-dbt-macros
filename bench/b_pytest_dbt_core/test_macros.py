import pytest


def norm(s):
    return " ".join(s.split())


def check(gen, args, expected):
    assert norm(gen(*args)) == norm(expected)


@pytest.mark.parametrize("macro_generator", ["macro.dbt_utils.generate_surrogate_key"], indirect=True)
def test_surrogate_key(macro_generator):
    check(macro_generator, [["order_id", "customer_id"]],
          "md5(cast(coalesce(cast(order_id as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || "
          "coalesce(cast(customer_id as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT))")


@pytest.mark.parametrize("macro_generator", ["macro.dbt_utils.deduplicate"], indirect=True)
def test_deduplicate(macro_generator):
    check(macro_generator, ["my_table", "user_id", "updated_at desc"],
          """with row_numbered as ( select _inner.*, row_number() over ( partition by user_id
          order by updated_at desc ) as rn from my_table as _inner ) select distinct data.*
          from my_table as data natural join row_numbered where row_numbered.rn = 1""")


@pytest.mark.parametrize("macro_generator", ["macro.dbt.dateadd"], indirect=True)
def test_dateadd(macro_generator):
    check(macro_generator, ["day", 7, "order_date"], "(order_date + cast(7 as bigint) * interval 1 day)")


@pytest.mark.parametrize("macro_generator", ["macro.dbt.datediff"], indirect=True)
def test_datediff(macro_generator):
    check(macro_generator, ["start_ts", "end_ts", "hour"],
          "(date_diff('hour', start_ts::timestamp, end_ts::timestamp ))")


@pytest.mark.parametrize("macro_generator", ["macro.dbt_utils.haversine_distance"], indirect=True)
def test_haversine(macro_generator):
    check(macro_generator, ["lat1", "lon1", "lat2", "lon2"],
          "2 * 3961 * asin(sqrt(power((sin(radians((lat2 - lat1) / 2))), 2) + cos(radians(lat1)) * "
          "cos(radians(lat2)) * power((sin(radians((lon2 - lon1) / 2))), 2))) * 1")

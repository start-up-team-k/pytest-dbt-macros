import sys

import pytest

from pytest_dbt_macros import CompilationError, MacroProject, assert_sql_equal


def test_macro_raising_compiler_error(dbt_macros):
    assert dbt_macros.require_positive(3).strip() == "3"
    with pytest.raises(CompilationError, match="n must be positive, got 0"):
        dbt_macros.require_positive(0)


def test_package_namespace_and_project_macro(dbt_macros):
    assert_sql_equal(dbt_macros.dbt_utils.safe_add(["a", "b"]), "coalesce(a, 0) + coalesce(b, 0)")
    assert_sql_equal(dbt_macros.cedar_fixture.to_text("x"), "cast(x as TEXT)")
    with pytest.raises(AttributeError):
        dbt_macros.dbt_utils.no_such_macro


def test_target_type_changes_the_branch(dbt_macros):
    dbt_macros.target["type"] = "bigquery"
    assert_sql_equal(dbt_macros.to_text("x"), "safe_cast(x as string)")
    dbt_macros.target["type"] = "postgres"
    assert_sql_equal(dbt_macros.to_text("x"), "cast(x as TEXT)")


def test_dispatch_uses_parent_adapter(dbt_macros):
    dbt_macros.target["type"] = "postgres"
    expected = dbt_macros.render("{{ dbt.dateadd('day', 1, 'd') }}")
    dbt_macros.target["type"] = "redshift"  # dispatch: redshift__ -> postgres__ -> default__
    assert dbt_macros.render("{{ dbt.dateadd('day', 1, 'd') }}") == expected


def test_dispatch_config_overrides_package_macro(dbt_macros):
    # fixture dbt_project.yml puts the root project first in dbt_utils' search order
    assert_sql_equal(dbt_macros.dbt_utils.safe_divide("a", "b"), "((a) * 1.0) / nullif((b), 0)")
    dbt_macros.dispatch[0]["search_order"] = ["dbt_utils", "cedar_fixture"]  # reversed: the package wins
    assert_sql_equal(dbt_macros.dbt_utils.safe_divide("a", "b"), "(a) / nullif((b), 0)")


def test_dispatch_error_lists_search_order(dbt_macros):
    with pytest.raises(CompilationError, match="Searched for: 'postgres__nope', 'default__nope'"):
        dbt_macros.render("{{ adapter.dispatch('nope')() }}")


def test_var_and_env_var(dbt_macros):
    assert_sql_equal(dbt_macros.tz_expr("c"), "c at time zone 'UTC'")
    dbt_macros.vars["tz"] = "Asia/Seoul"
    assert "Asia/Seoul" in dbt_macros.tz_expr("c")
    assert dbt_macros.render("{{ var('missing', 7) }}") == "7"
    with pytest.raises(CompilationError, match="Required var 'missing'"):
        dbt_macros.render("{{ var('missing') }}")
    dbt_macros.env["FOO"] = "bar"
    assert dbt_macros.render("{{ env_var('FOO') }}") == "bar"
    with pytest.raises(CompilationError, match="NOPE_NOT_SET"):
        dbt_macros.render("{{ env_var('NOPE_NOT_SET') }}")


def test_database_features_fail_loudly(dbt_macros):
    with pytest.raises(CompilationError, match="needs a database"):
        dbt_macros.render("{{ run_query('select 1') }}")
    with pytest.raises(CompilationError, match="adapter.get_columns_in_relation"):
        dbt_macros.render("{{ adapter.get_columns_in_relation(ref('m')) }}")


def test_does_not_import_dbt(dbt_macros):
    dbt_macros.dbt_utils.generate_surrogate_key(["a"])
    assert "dbt" not in sys.modules


def test_assert_sql_equal():
    assert_sql_equal("SELECT  a,b\nFROM t", "select a, b from t")
    with pytest.raises(AssertionError):
        assert_sql_equal("select a from t", "select b from t")
    assert_sql_equal("Select 1", "select 1", dialect="snowflake")


def test_missing_project_dir_has_only_dbt_macros(tmp_path):
    p = MacroProject(tmp_path)
    assert p.render("{{ dbt.concat(['a', 'b']) }}") == "a || b"

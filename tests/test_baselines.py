"""Every case in baselines/cases.json is rendered per target type and compared with what `dbt compile`
produced for the same Jinja (see scripts/make_baselines.sh and baselines/VERSIONS.txt)."""
import json
from pathlib import Path

import pytest

from pytest_dbt_macros import assert_sql_equal

BASE = Path(__file__).parent / "baselines"
CASES = json.loads((BASE / "cases.json").read_text())
TARGETS = sorted(p.name for p in BASE.iterdir() if p.is_dir())


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_matches_dbt_compile(dbt_macros, target, case):
    dbt_macros.target["type"] = target
    actual = dbt_macros.render(CASES[case])
    expected = (BASE / target / f"{case}.sql").read_text()
    assert_sql_equal(actual, expected, dialect=None if target == "duckdb" else target)

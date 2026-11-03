from pathlib import Path

import pytest

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "project"


@pytest.fixture
def dbt_project_dir():
    return FIXTURE_PROJECT

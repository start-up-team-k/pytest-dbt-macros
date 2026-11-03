import pytest

from .core import MacroProject


@pytest.fixture
def dbt_project_dir(request):
    """Directory holding dbt_project.yml (default: where pytest was started). Override this fixture to point elsewhere."""
    return request.config.invocation_params.dir


@pytest.fixture
def dbt_macros(dbt_project_dir):
    """The project's macros as Python callables; see MacroProject."""
    return MacroProject(dbt_project_dir)

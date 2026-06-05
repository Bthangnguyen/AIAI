import pytest
from fastapi import HTTPException

from src.core.solvers.factory import SolverFactory


def test_solver_factory_rejects_non_string_solver_type():
    with pytest.raises(HTTPException) as exc_info:
        SolverFactory.create(None, {})

    assert exc_info.value.status_code == 400
    assert "Solver type" in exc_info.value.detail


def test_solver_factory_rejects_non_dict_problem():
    with pytest.raises(HTTPException) as exc_info:
        SolverFactory.create("ortools", [])

    assert exc_info.value.status_code == 400
    assert "Problem" in exc_info.value.detail

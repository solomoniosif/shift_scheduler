from ortools.sat.python import cp_model
import pytest

try:
    from shift_scheduler.solver import ScheduleModel, SolutionCollector
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))
    from shift_scheduler.solver import ScheduleModel, SolutionCollector


def test_model_variables_created(model):
    assert model.variables


def test_model_variables_types(model):
    assert type(model.variables) == dict
    for var in model.variables:
        assert type(model.variables[var]) == cp_model.IntVar


def test_model_variables_valid_nurse_positions(schedule, model):
    for n_id, t_id, s_id in model.variables:
        nurse = schedule.nurses_lookup[n_id]
        position_id = int(str(s_id)[-2:])
        position = schedule.positions_lookup[position_id]

        assert position.sector.short_name in nurse.positions


@pytest.mark.xfail
def test_solver_status_name(model, cp_solver, solution_printer):
    cp_solver.Solve(model, solution_printer)
    assert cp_solver.StatusName() == 'OPTIMAL'

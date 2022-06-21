import pytest

try:
    from shift_scheduler.solver import ScheduleModel, SolutionCollector
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))
    from shift_scheduler.solver import ScheduleModel, SolutionCollector


@pytest.mark.xfail
def test_solver_status_name(model, cp_solver, solution_printer):
    cp_solver.Solve(model, solution_printer)
    assert cp_solver.StatusName() == 'OPTIMAL'

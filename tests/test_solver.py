from ortools.sat.python import cp_model
import pytest

try:
    from shift_scheduler import interface, models, solver
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))
    from shift_scheduler import interface, models, solver


#################################
#   Tests for ScheduleModel     #
#################################


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


def test_solution_types(solution):
    assert type(solution) == dict
    for n in solution:
        assert type(n) == models.Nurse
        assert type(solution[n]) == list
        assert all((True if type(s) == models.Shift else False for s in solution[n]))


def test_solution_correct_number_of_shifts_planned(solution, schedule):
    for nurse in solution:
        assert len(solution[nurse]) == schedule.shifts_to_work_per_nurse[nurse]


def test_solution_nurse_can_work_planned_position(solution, schedule):
    for nurse in solution:
        for shift in solution[nurse]:
            assert shift.position.sector.short_name in nurse.positions


def test_solution_by_timeslot_types(solution_by_timeslot):
    assert type(solution_by_timeslot) == dict
    for timeslot in solution_by_timeslot:
        assert type(timeslot) == models.TimeSlot
        assert type(solution_by_timeslot[timeslot]) == list
        assert all((True if type(s) == models.Shift else False for s in solution_by_timeslot[timeslot]))


def test_min_positions_covered(solution_by_timeslot, schedule):
    min_positions = set(schedule.positions[:11])
    for timeslot in solution_by_timeslot:
        ts_positions = [shift.position for shift in solution_by_timeslot[timeslot]]
        assert min_positions.issubset(ts_positions)


def test_solution_min_positions_planned(solution, schedule):
    for nurse in schedule.nurse_position_ranges:
        for sector in schedule.nurse_position_ranges[nurse]:
            min_sector_shifts = schedule.nurse_position_ranges[nurse][sector]['min']
            if min_sector_shifts:
                assert len([s for s in solution[nurse] if s.position.sector == sector]) >= min_sector_shifts


def test_solution_max_positions_planned(solution, schedule):
    for nurse in schedule.nurse_position_ranges:
        for sector in schedule.nurse_position_ranges[nurse]:
            max_sector_shifts = schedule.nurse_position_ranges[nurse][sector]['max']
            if max_sector_shifts:
                assert len([s for s in solution[nurse] if s.position.sector == sector]) <= max_sector_shifts


###############################################
#   Tests for NurseCycleDistributionModel     #
###############################################

def test_ncd_model_variables(ncd_model):
    assert ncd_model.variables


def test_ncd_model_variables_types(ncd_model):
    assert type(ncd_model.variables) == dict
    for var in ncd_model.variables:
        assert type(ncd_model.variables[var]) == cp_model.IntVar

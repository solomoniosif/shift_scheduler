from datetime import date

import pytest
from ortools.sat.python import cp_model

try:
    from shift_scheduler import interface, models, solver
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))

    from shift_scheduler import interface, models, solver


########################################
#   Fixtures for ScheduleSSManager     #
########################################

@pytest.fixture(scope="session")
def ss_manager():
    ss_manager = interface.ScheduleSSManager(2022, 5)
    ss_manager.get_or_create_new_ss()
    return ss_manager


########################################
#   Fixtures for Timeslot              #
########################################

@pytest.fixture(scope="session")
def sample_timeslot():
    return models.TimeSlot(date(2022, 1, 1), 1)


@pytest.fixture(scope="session")
def all_month_timeslots(sample_month):
    all_timeslots = []
    for d in sample_month.days_list:
        for p in [1, 2]:
            all_timeslots.append(models.TimeSlot(d, p))
    return all_timeslots


########################################
#   Fixtures for Month                 #
########################################

@pytest.fixture(scope="session")
def january_legal_holidays():
    return [date(2022, 1, 1), date(2022, 1, 2), date(2022, 1, 24)]


@pytest.fixture(scope="session")
def sample_month(january_legal_holidays):
    return models.Month(2022, 1, january_legal_holidays)


########################################
#   Fixtures for Sector                #
########################################

@pytest.fixture(scope="session")
def all_sectors(ss_manager):
    sectors = []
    for row in ss_manager.sector_list:
        if row[1] != "":
            sectors.append(
                models.Sector(
                    id=int(row[0]),
                    short_name=row[2],
                    full_name=row[1],
                    min_nurses=int(row[3]),
                    optimal_nurses=int(row[4]),
                    max_nurses=int(row[5]),
                )
            )
    return sectors


@pytest.fixture(scope="session")
def sectors_lookup(all_sectors):
    return {s.short_name: s for s in all_sectors}


@pytest.fixture(scope="session")
def sample_sectors():
    sectors_data = [
        [1, 'Responsabil tura', 'Rt', 1, 1, 1],
        [2, 'Triaj', 'T', 1, 1, 2],
        [3, 'Resuscitare', 'RCP', 1, 1, 2],
        [4, 'Urgente majore', 'A', 2, 2, 4],
        [5, 'Urgente minore', 'M', 2, 2, 4],
        [6, 'Urgente minore Etaj', 'Me', 1, 1, 2],
        [7, 'Chirurgie', 'Ch', 0, 1, 1],
        [8, 'Laborator', 'L', 1, 1, 1],
        [9, 'Triaj epidemiologic 1', 'C1', 1, 1, 1],
        [10, 'Triaj epidemiologic 2', 'C2', 0, 1, 2],
        [11, 'Transport neonatal', 'Nn', 1, 1, 2],
        [12, 'SMURD', 'S', 1, 1, 2],
        [13, 'Elicopter Jibou', 'E', 0, 1, 1],
        [14, '8', '8', 0, 1, 2],
        [15, '12', '12', 0, 0, 3]

    ]
    sample_sectors = []
    for row in sectors_data:
        all_sectors.append(models.Sector(row[0], row[2], row[1], row[3], row[4], row[5]))
    return sample_sectors


########################################
#   Fixtures for Position              #
########################################

@pytest.fixture(scope="session")
def sample_position():
    return models.Position(1, 'Rt', models.Sector(1, 'Rt', 'Responsabil tura', 1, 1, 1))


@pytest.fixture(scope="session")
def all_positions(ss_manager, sectors_lookup):
    positions = []
    for row in ss_manager.position_list:
        if row[2] != "":
            id = int(row[0])
            name = row[2]
            sector = sectors_lookup[row[1]]
            positions.append(models.Position(id, name, sector))
    return positions


########################################
#   Fixtures for Nurses                #
########################################

@pytest.fixture(scope="session")
def all_nurses(ss_manager):
    nurses = []
    for row in ss_manager.nurse_list:
        if row[1] != "":
            nurse_id = int(row[0])
            full_name = row[1]
            first_name = full_name.split(" ")[0]
            last_name = full_name.split(" ")[-1]
            shift_cycle = int(row[4]) if row[4].isnumeric() else row[4]
            sectors_raw = row[5:]
            sectors = [s for s in sectors_raw if s != ""]
            extra_hours_worked = int(row[3])
            nurses.append(
                models.Nurse(
                    id=nurse_id,
                    first_name=first_name,
                    last_name=last_name,
                    positions=sectors,
                    cycle=shift_cycle,
                    extra_hours_worked=extra_hours_worked,
                )
            )
    return nurses


@pytest.fixture(scope="session")
def sample_nurse():
    return models.Nurse(99, "John", "Doe", ['Rt', 'T', 'RCP', 'A', 'M', 'Me', 'Ch', 'L', 'Nn', 'S', 'E'], cycle=1)


@pytest.fixture(scope="session")
def sample_shift(sample_timeslot, sample_position):
    return models.Shift(sample_timeslot, sample_position)


########################################
#   Fixtures for Shift                 #
########################################

@pytest.fixture(scope="session")
def all_shifts(all_timeslots, all_positions):
    all_shifts = []
    for t in all_timeslots:
        for p in all_positions:
            all_shifts.append(models.Shift(t, p))
    return all_shifts


@pytest.fixture(scope="session")
def sample_shift(sample_timeslot, sample_position):
    return models.Shift(sample_timeslot, sample_position)


########################################
#   Fixtures for Schedule              #
########################################

@pytest.fixture(scope="session")
def schedule(ss_manager):
    return models.Schedule(ss_manager)


########################################
#   Fixtures for ScheduleModel         #
########################################

@pytest.fixture(scope="session")
def model(schedule):
    return solver.ScheduleModel(schedule)


@pytest.fixture(scope="session")
def cp_solver():
    return cp_model.CpSolver()


@pytest.fixture(scope="session")
def solution_printer(model, schedule):
    return solver.SolutionCollector(model.variables, schedule)


######################################################
#   Fixtures for NurseCycleDistributionModel         #
######################################################

@pytest.fixture(scope="session")
def ncd_model(schedule):
    return solver.NurseCycleDistributionModel(schedule)


@pytest.fixture(scope="session")
def ncd_solution_collector(ncd_model, schedule):
    return solver.NurseDistributionSolutionCollector(ncd_model.variables, schedule)

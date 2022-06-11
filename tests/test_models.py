from datetime import date

import pytest

try:
    from shift_scheduler import models
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))

    from shift_scheduler import models


#################################
#   Tests for TimeSlot Class    #
#################################

@pytest.fixture()
def sample_timeslot():
    return models.TimeSlot(date(2022, 1, 1), 1)


def test_timeslot_date(sample_timeslot):
    assert sample_timeslot.day.day == 1
    assert sample_timeslot.day.month == 1
    assert sample_timeslot.day.year == 2022
    assert sample_timeslot.day == date(2022, 1, 1)


def test_timeslot_part(sample_timeslot):
    assert sample_timeslot.part == 1


def test_timeslot_part_name(sample_timeslot):
    assert sample_timeslot.part_name == "Z"


def test_timeslot_id(sample_timeslot):
    assert sample_timeslot.id == 1


def test_timeslot_ts_id(sample_timeslot):
    assert sample_timeslot.ts_id == 0


def test_timeslot_cycle(sample_timeslot):
    assert sample_timeslot.cycle == 3


def test_timeslot_overlaps_with_function(sample_timeslot):
    assert sample_timeslot.overlaps_with([date(2022, 1, 1)])
    assert not sample_timeslot.overlaps_with([date(2022, 1, 2)])
    jan_2022 = [date(2022, 1, d) for d in range(1, 31)]
    assert sample_timeslot.overlaps_with(jan_2022)


def test_timeslot_is_adjacent_ts_function(sample_timeslot):
    assert sample_timeslot.is_adjacent_timeslot(models.TimeSlot(date(2022, 1, 1), 2))
    assert not sample_timeslot.is_adjacent_timeslot(models.TimeSlot(date(2022, 1, 2), 1))


#################################
#   Tests for Month Class       #
#################################


@pytest.fixture()
def january_legal_holidays():
    return [date(2022, 1, 1), date(2022, 1, 2), date(2022, 1, 24)]


@pytest.fixture()
def sample_month(january_legal_holidays):
    return models.Month(2022, 1, january_legal_holidays)


def test_month_date(sample_month):
    assert sample_month.year == 2022
    assert sample_month.month == 1


def test_month_name(sample_month):
    assert sample_month.month_name == "Ianuarie"


def test_month_num_days(sample_month):
    assert sample_month.num_days == 31


def test_month_days_list(sample_month):
    assert sample_month.days_list == [date(2022, 1, d) for d in range(1, 32)]


def test_month_working_days(sample_month, january_legal_holidays):
    assert len(sample_month.working_days) == 20
    assert sample_month.working_days == [
        date(2022, 1, d) for d in range(1, 32) if
        date(2022, 1, d).weekday() < 5
        and date(2022, 1, d) not in january_legal_holidays
    ]


def test_month_num_working_days(sample_month):
    assert sample_month.num_working_days == 20


def test_month_first_cycle(sample_month):
    assert sample_month.first_cycle == 3


def test_month_get_cycle_of_timeslot(sample_month):
    assert sample_month.get_cycle_of_timetslot(date(2022, 1, 2), 1) == 4


def test_month_num_working_hours(sample_month):
    assert sample_month.num_working_hours(8) == 160


def test_month_monthly_shifts_per_cycle(sample_month):
    assert sample_month.monthly_shifts_per_cycle[1] == 15
    assert sample_month.monthly_shifts_per_cycle[2] == 15
    assert sample_month.monthly_shifts_per_cycle[3] == 16
    assert sample_month.monthly_shifts_per_cycle[4] == 16


def test_month_timeslots(sample_month):
    assert len(sample_month.timeslots) == 62
    assert all((True if type(ts) == models.TimeSlot else False for ts in sample_month.timeslots))


def test_month_timeslots_per_cycle(sample_month):
    assert len(sample_month.timeslots_per_cycle[1]) == 15
    assert len(sample_month.timeslots_per_cycle[2]) == 15
    assert len(sample_month.timeslots_per_cycle[3]) == 16
    assert len(sample_month.timeslots_per_cycle[4]) == 16
    for cycle in [1, 2, 3, 4]:
        assert all((True if type(ts) == models.TimeSlot else False for ts in sample_month.timeslots_per_cycle[cycle]))
        assert all((True if ts.cycle == cycle else False for ts in sample_month.timeslots_per_cycle[cycle]))


#################################
#   Tests for Sector Class      #
#################################


@pytest.fixture()
def all_sectors():
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
    all_sectors = []
    for row in sectors_data:
        all_sectors.append(models.Sector(row[0], row[2], row[1], row[3], row[4], row[5]))
    return all_sectors


def test_all_sectors(all_sectors):
    assert all((True if type(s) == models.Sector else False for s in all_sectors))
    assert len({s.id for s in all_sectors}) == 15


def test_all_sectors_min_lte_max_nurses(all_sectors):
    for sector in all_sectors:
        assert sector.min_nurses <= sector.max_nurses


def test_sector_name_is_string(all_sectors):
    for sector in all_sectors:
        assert type(sector.full_name) == str
        assert type(sector.short_name) == str


def test_sector_min_max_optimal_is_int(all_sectors):
    for sector in all_sectors:
        assert type(sector.min_nurses) == int
        assert type(sector.optimal_nurses) == int
        assert type(sector.max_nurses) == int

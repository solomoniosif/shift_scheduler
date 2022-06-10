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
    assert sample_month.working_days == [date(2022, 1, d) for d in range(1, 32) if
                                         date(2022, 1, d).weekday() < 5 and date(2022, 1,
                                                                                 d) not in january_legal_holidays]


def test_month_num_working_days(sample_month):
    assert sample_month.num_working_days == 20


def test_month_first_cycle(sample_month):
    assert sample_month.first_cycle == 3


def test_month_get_cycle_of_timeslot(sample_month):
    assert sample_month.get_cycle_of_timetslot(date(2022, 1, 2), 1) == 4

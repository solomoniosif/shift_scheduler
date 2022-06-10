from datetime import date

import pytest

try:
    from shift_scheduler.models import TimeSlot, Month, Sector, Position, Nurse, Shift, Schedule
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))

    from shift_scheduler.models import TimeSlot, Month, Sector, Position, Nurse, Shift, Schedule


@pytest.fixture()
def sample_timeslot():
    return TimeSlot(date(2022, 1, 1), 1)


def test_timeslot_date(sample_timeslot):
    assert sample_timeslot.day.day == 1
    assert sample_timeslot.day.month == 1
    assert sample_timeslot.day.year == 2022


def test_timeslot_part(sample_timeslot):
    assert sample_timeslot.part == 1


def test_timeslot_part_name(sample_timeslot):
    assert sample_timeslot.part_name == "Z"

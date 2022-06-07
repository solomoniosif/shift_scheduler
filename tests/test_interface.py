import pytest

from shift_scheduler import interface


@pytest.fixture()
def ss_manager():
    return interface.ScheduleSSManager(2022, 5)


def test_year(ss_manager):
    assert ss_manager.year == 2022


def test_year_type(ss_manager):
    assert type(ss_manager.year) == int


def test_month(ss_manager):
    assert ss_manager.month == 5


def test_month_type(ss_manager):
    assert type(ss_manager.month) == int


def test_month_name(ss_manager):
    assert ss_manager.month_name == "Mai"


def test_month_days(ss_manager):
    assert ss_manager.month_days == 31


def test_non_working_days_number(ss_manager):
    assert len(ss_manager.non_working_days) == 9
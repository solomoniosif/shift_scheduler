from datetime import date

import pytest

try:
    from shift_scheduler import interface, models
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))

    from shift_scheduler import interface, models


#################################
#   Tests for TimeSlot Class    #
#################################


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


def test_all_sectors(all_sectors):
    assert all((True if type(s) == models.Sector else False for s in all_sectors))
    assert len({s.id for s in all_sectors}) == 15


def test_sector_min_lte_max_nurses(all_sectors):
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


#################################
#   Tests for Position Class    #
#################################


def test_position_sector_type(sample_position, all_positions):
    assert type(sample_position.sector) == models.Sector
    for position in all_positions:
        assert type(position.sector) == models.Sector


def test_different_position_ids(all_positions):
    assert len(all_positions) == len({p.id for p in all_positions})


def test_position_eq(all_positions, sectors_lookup):
    assert all_positions[0] != all_positions[1]
    assert all_positions[0] == models.Position(1, 'Rt', sectors_lookup['Rt'])


#################################
#   Tests for Nurse Class       #
#################################


def test_unique_nurse_id(all_nurses):
    assert len(all_nurses) == len({nurse.id for nurse in all_nurses})


def test_nurse_shifts_to_work(sample_nurse, sample_month):
    assert sample_nurse.shifts_to_work(sample_month) == 14
    assert sample_nurse.shifts_to_work(sample_month, off_days=3) == 12


def test_nurse_can_work_shift(sample_nurse, sample_shift):
    assert not sample_nurse.can_work_shift(sample_shift)
    assert sample_nurse.can_work_shift(sample_shift, off_cycle=True)


#################################
#   Tests for Shift Class       #
#################################

def test_shift_no_assigned_nurse(sample_shift):
    assert not sample_shift.assigned_nurse


def test_correct_shift_cycle(sample_shift, sample_timeslot):
    assert sample_shift.cycle == sample_timeslot.cycle


#################################
#   Tests for Schedule Class    #
#################################

def test_schedule_year_month(schedule, ss_manager):
    assert schedule.year == ss_manager.year
    assert schedule.mnth == ss_manager.month


def test_schedule_month_type(schedule):
    assert type(schedule.month) == models.Month


def test_schedule_all_nurses_initialized(schedule, all_nurses):
    assert len(schedule.nurses) == 85
    assert len(schedule.nurses) == len(all_nurses)


def test_schedule_available_nurses_filtered_correctly(schedule):
    for nurse in schedule.available_nurses:
        assert nurse.cycle in [1, 2, 3, 4]


def test_schedule_heli_nurses(schedule):
    for nurse in schedule.heli_nurses:
        assert 'E' in nurse.positions


def test_schedule_all_sectors_initialized(schedule, all_sectors):
    assert len(schedule.sectors) == 15
    assert len(schedule.sectors) == len(all_sectors)


def test_schedule_all_positions_initialized(schedule, all_positions):
    assert len(schedule.positions) == 20
    assert len(schedule.positions) == len(all_positions)


def test_schedule_nurse_position_ranges(schedule):
    assert type(schedule.nurse_position_ranges) == dict
    assert len(schedule.nurse_position_ranges) == len(schedule.nurses)


def test_schedule_rest_leave_days(schedule):
    assert type(schedule.rest_leave_days) == dict
    assert len(schedule.rest_leave_days) == len(schedule.nurses)
    for nurse in schedule.rest_leave_days:
        assert type(schedule.rest_leave_days[nurse]) == list
        if schedule.rest_leave_days[nurse]:
            assert all((True if type(d) == date else False for d in schedule.rest_leave_days[nurse]))


def test_schedule_off_days(schedule):
    assert type(schedule.off_days) == dict
    assert len(schedule.off_days) == len(schedule.nurses)
    for nurse in schedule.off_days:
        assert len(schedule.off_days[nurse]) <= len(schedule.rest_leave_days[nurse])


def test_schedule_all_off_days_are_working_days(schedule):
    for nurse in schedule.off_days:
        if schedule.off_days[nurse]:
            for day in schedule.off_days[nurse]:
                assert day.weekday() < 5


def test_schedule_fixed_assignments(schedule):
    assert type(schedule.fixed_assignments) == list
    if schedule.fixed_assignments:
        for shift in schedule.fixed_assignments:
            assert type(shift) == models.Shift
            assert shift.assigned_nurse


def test_schedule_off_cycle_shifts_from_fixed_assignments(schedule):
    assert type(schedule.off_cycle_shifts_from_fixed_assignments) == list
    if schedule.off_cycle_shifts_from_fixed_assignments:
        for shift in schedule.off_cycle_shifts_from_fixed_assignments:
            assert type(shift) == models.Shift
            assert shift.cycle != shift.assigned_nurse.cycle


def test_schedule_off_cycle_fixed_assignments_per_nurse(schedule):
    assert type(schedule.off_cycle_fixed_assignments_per_nurse) == dict
    for nurse in schedule.off_cycle_fixed_assignments_per_nurse:
        if schedule.off_cycle_fixed_assignments_per_nurse[nurse]:
            assert type(schedule.off_cycle_fixed_assignments_per_nurse[nurse]) == list
            assert all((True if type(s) == models.Shift else False for s in
                        schedule.off_cycle_fixed_assignments_per_nurse[nurse]))


def test_schedule_available_nurses_per_position_per_timeslot(schedule):
    assert type(schedule.available_nurses_per_position_per_timeslot) == dict
    for timeslot, position in schedule.available_nurses_per_position_per_timeslot:
        assert type(schedule.available_nurses_per_position_per_timeslot[(timeslot, position)]) == list
        assert len(schedule.available_nurses_per_position_per_timeslot[(timeslot, position)]) >= 1


def test_schedule_timeslots_with_skill_deficit(schedule):
    assert type(schedule.timeslots_with_skill_deficit) == dict
    for timeslot, position in schedule.timeslots_with_skill_deficit:
        assert type(schedule.timeslots_with_skill_deficit[(timeslot, position)]) == list
        assert len(schedule.timeslots_with_skill_deficit[(timeslot, position)]) <= 3
        assert position in ('Rt', 'Nn', 'S')


def test_schedule_shifts_to_work_per_nurse(schedule):
    assert type(schedule.shifts_to_work_per_nurse) == dict
    assert len(schedule.shifts_to_work_per_nurse) == len(schedule.available_nurses)
    for nurse in schedule.shifts_to_work_per_nurse:
        assert type(schedule.shifts_to_work_per_nurse[nurse]) == int
        assert schedule.shifts_to_work_per_nurse[nurse] <= 16


def test_schedule_shifts_to_work_per_cycle(schedule):
    assert type(schedule.shifts_to_work_per_cycle) == dict
    for cycle in schedule.shifts_to_work_per_cycle:
        assert type(schedule.shifts_to_work_per_cycle[cycle]) == int


def test_schedule_updated_shifts_to_work_per_cycle(schedule):
    assert type(schedule.updated_shifts_to_work_per_cycle) == dict
    for cycle in schedule.updated_shifts_to_work_per_cycle:
        assert type(schedule.updated_shifts_to_work_per_cycle[cycle]) == int


def test_schedule_check_total_shifts_to_work(schedule):
    total_stw_per_nurse = sum([schedule.shifts_to_work_per_nurse[nurse] for nurse in schedule.shifts_to_work_per_nurse])
    total_stw_per_cycle = sum(schedule.shifts_to_work_per_cycle[cycle] for cycle in schedule.shifts_to_work_per_cycle)
    assert total_stw_per_nurse == total_stw_per_cycle


def test_schedule_available_nurses_per_timeslot(schedule):
    assert type(schedule.available_nurses_per_timeslot) == dict
    for ts in schedule.available_nurses_per_timeslot:
        assert type(schedule.available_nurses_per_timeslot[ts]) == list
        assert all((True if type(n) == models.Nurse else False for n in schedule.available_nurses_per_timeslot[ts]))
        assert len(schedule.available_nurses_per_timeslot[ts]) >= 9


def test_schedule_available_timeslots_per_nurse(schedule):
    assert type(schedule.available_timeslots_per_nurse) == dict
    for nurse in schedule.available_timeslots_per_nurse:
        assert type(schedule.available_timeslots_per_nurse[nurse]) == list
        assert all(
            (True if type(ts) == models.TimeSlot else False for ts in schedule.available_timeslots_per_nurse[nurse]))


def test_schedule_nurses_with_not_enough_cycle_timeslots(schedule):
    assert type(schedule.nurses_with_not_enough_cycle_timeslots) == dict
    for nurse in schedule.nurses_with_not_enough_cycle_timeslots:
        assert type(schedule.nurses_with_not_enough_cycle_timeslots[nurse]['extra_timeslots_needed']) == int
        assert nurse in schedule.available_nurses
        assert schedule.shifts_to_work_per_nurse[nurse] > len(schedule.available_timeslots_per_nurse[nurse])


def test_schedule_timeslots_ordered_by_num_nurses(schedule):
    assert type(schedule.timeslots_ordered_by_num_nurses) == list
    for i in range(1, len(schedule.timeslots_ordered_by_num_nurses)):
        assert type(schedule.timeslots_ordered_by_num_nurses[i]) == list
        assert len(schedule.timeslots_ordered_by_num_nurses[i]) == 2
        assert schedule.timeslots_ordered_by_num_nurses[i][1] >= schedule.timeslots_ordered_by_num_nurses[i - 1][1]


def test_schedule_possible_extra_ts_for_nurses_with_ts_deficit(schedule):
    assert type(schedule.possible_extra_ts_for_nurses_with_ts_deficit) == dict
    for nurse in schedule.possible_extra_ts_for_nurses_with_ts_deficit:
        assert nurse in schedule.nurses_with_not_enough_cycle_timeslots
        assert type(schedule.possible_extra_ts_for_nurses_with_ts_deficit[nurse]) == list
        assert all((True if type(t) == models.TimeSlot else False for t in
                    schedule.possible_extra_ts_for_nurses_with_ts_deficit[nurse]))


def test_schedule_extra_ts_for_nurses_with_ts_deficit(schedule):
    assert type(schedule.extra_ts_for_nurses_with_ts_deficit) == dict
    for nurse in schedule.extra_ts_for_nurses_with_ts_deficit:
        assert type(schedule.extra_ts_for_nurses_with_ts_deficit[nurse]) == list
        assert len(schedule.extra_ts_for_nurses_with_ts_deficit[nurse]) == \
               schedule.nurses_with_not_enough_cycle_timeslots[nurse]['extra_timeslots_needed']


def test_schedule_initial_nurses_per_timeslot(schedule):
    assert type(schedule.initial_nurses_per_timeslot) == dict
    for ts in schedule.initial_nurses_per_timeslot:
        assert type(schedule.initial_nurses_per_timeslot[ts]) == dict
        assert type(schedule.initial_nurses_per_timeslot[ts]['num_nurses']) == int
        assert 9 <= schedule.initial_nurses_per_timeslot[ts]['num_nurses'] <= 20


def test_schedule_updated_nurses_per_timeslot(schedule):
    assert type(schedule.updated_nurses_per_timeslot) == dict
    for ts in schedule.updated_nurses_per_timeslot:
        assert type(schedule.updated_nurses_per_timeslot[ts]) == dict
        assert type(schedule.updated_nurses_per_timeslot[ts]['num_nurses']) == int
        assert 9 <= schedule.updated_nurses_per_timeslot[ts]['num_nurses'] <= 20


def test_schedule_check_all_shifts_to_work_planned(schedule):
    total_stw = sum([schedule.shifts_to_work_per_nurse[nurse] for nurse in schedule.shifts_to_work_per_nurse])
    total_initial_shiftslots_planned = sum(
        [schedule.initial_nurses_per_timeslot[ts]['num_nurses'] for ts in schedule.initial_nurses_per_timeslot])
    total_off_cycle_timeslots = sum(
        schedule.nurses_with_not_enough_cycle_timeslots[nurse]['extra_timeslots_needed'] for nurse in
        schedule.nurses_with_not_enough_cycle_timeslots)
    assert total_stw == total_initial_shiftslots_planned + total_off_cycle_timeslots
    updated_total_shiftslots_planned = sum(
        [schedule.updated_nurses_per_timeslot[ts]['num_nurses'] for ts in schedule.updated_nurses_per_timeslot])
    assert total_stw == updated_total_shiftslots_planned

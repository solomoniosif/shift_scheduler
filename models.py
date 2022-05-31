import copy
import logging
import math
import random
from calendar import monthrange
from datetime import date, timedelta
from functools import cached_property, reduce
from typing import List, Dict

from interface import ScheduleSSManager
from utils import TimerLog

ZERO_DAY = date(2022, 1, 1)
CYCLE_SUCCESSION = [3, 1, 4, 3, 2, 4, 1, 2]

logger = logging.getLogger('scheduler.models')


class TimeSlot:
    def __init__(self, day: date, part: int):
        self.day = day
        self.part = part
        self.part_names = ["Z", "N"]
        self.part_name = self.part_names[self.part - 1]

    @property
    def id(self):
        return self.day.day * 2 + self.part - 2

    @property
    def ts_id(self) -> int:
        days_delta = (self.day - ZERO_DAY).days
        return days_delta * 2 + (self.part - 1)

    @property
    def cycle(self) -> int:
        return CYCLE_SUCCESSION[self.ts_id % 8]

    def overlaps_with(self, days_list):
        return self.day in days_list or (self.part == 2 and self.day + timedelta(days=1) in days_list)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.day == other.day and self.part == other.part

    def __repr__(self):
        return f"{self.day.day}/{self.day.month}/{self.day.year}-{self.part_name}"

    def __hash__(self):
        return hash((self.day, self.part))


class Month:
    """
    A class used to represent a calendar month for generating the schedule.
    It keeps track of working and non-working days
    """

    MONTH_NAMES = [
        "Ianuarie",
        "Februarie",
        "Martie",
        "Aprilie",
        "Mai",
        "Iunie",
        "Iulie",
        "August",
        "Septembrie",
        "Octombrie",
        "Noiembrie",
        "Decembrie",
    ]

    def __init__(self, year: int, month: int, holidays: List[date] = None):
        self.year = year
        self.month = month
        self.month_name = Month.MONTH_NAMES[self.month - 1]
        self.holidays = holidays

    @cached_property
    def num_days(self) -> int:
        return monthrange(self.year, self.month)[1]

    @cached_property
    def days_list(self) -> List[date]:
        return [date(self.year, self.month, d) for d in range(1, self.num_days + 1)]

    @cached_property
    def working_days(self) -> List[date]:
        working_days = []
        for d in range(1, self.num_days + 1):
            day = date(self.year, self.month, d)
            if day.weekday() < 5 and day not in self.holidays:
                working_days.append(day)
        return working_days

    @property
    def num_working_days(self) -> int:
        return len(self.working_days)

    @cached_property
    def non_working_days(self) -> List[date]:
        non_working_days = []
        for d in range(1, self.num_days + 1):
            day = date(self.year, self.month, d)
            if day.weekday() > 4 or day in self.holidays:
                non_working_days.append(day)
        return non_working_days

    @property
    def num_non_working_days(self) -> int:
        return len(self.non_working_days)

    def num_working_hours(self, daily_norm=8) -> int:
        return self.num_working_days * daily_norm

    @property
    def first_cycle(self) -> int:
        days_delta = (date(self.year, self.month, 1) - ZERO_DAY).days
        first_shift_id = days_delta * 2
        return CYCLE_SUCCESSION[first_shift_id % 8]

    @staticmethod
    def get_cycle_of_timetslot(day, part) -> int:
        days_delta = (day - ZERO_DAY).days
        shiftslot_id = days_delta * 2 + (part - 1)
        return CYCLE_SUCCESSION[shiftslot_id % 8]

    @property
    def monthly_shifts_per_cycle(self) -> Dict[int, int]:
        shifts_per_cycle = {1: 0, 2: 0, 3: 0, 4: 0}
        for day in self.days_list:
            for part in [1, 2]:
                current_cycle = self.get_cycle_of_timetslot(day, part)
                shifts_per_cycle[current_cycle] += 1
        return shifts_per_cycle

    @cached_property
    def timeslots(self) -> List[TimeSlot]:
        return [TimeSlot(d, p) for d in self.days_list for p in [1, 2]]

    @cached_property
    def timeslots_per_cycle(self) -> Dict[int, List[TimeSlot]]:
        cycle_1 = [ts for ts in self.timeslots if ts.cycle == 1]
        cycle_2 = [ts for ts in self.timeslots if ts.cycle == 2]
        cycle_3 = [ts for ts in self.timeslots if ts.cycle == 3]
        cycle_4 = [ts for ts in self.timeslots if ts.cycle == 4]
        return {1: cycle_1, 2: cycle_2, 3: cycle_3, 4: cycle_4}


class Sector:
    """
    A class used to represent a sector (work location / position) for nurses
    """

    def __init__(
            self,
            id: int,
            short_name: str,
            full_name: str,
            min_nurses: int,
            optimal_nurses: int,
            max_nurses: int,
            priority: int = 1,
            is_prehospital: bool = False,
    ):
        self.id = id
        self.short_name = short_name
        self.full_name = full_name
        self.min_nurses = min_nurses
        self.optimal_nurses = optimal_nurses
        self.max_nurses = max_nurses
        self.priority = priority
        self.is_prehospital = is_prehospital

    def __str__(self) -> str:
        return self.full_name

    def __repr__(self) -> str:
        return self.short_name


class Position:
    def __init__(self, id: int, name: str, sector: Sector):
        self.id = id
        self.name = name
        self.sector = sector

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        return self.id == other.id and self.sector == other.sector

    def __hash__(self):
        return hash((self.id, self.name, self.sector))


class Nurse:
    """
    A class used to represent a nurse
    """

    def __init__(
            self,
            id: int,
            first_name: str,
            last_name: str,
            positions: List[Sector],
            cycle=None,
            is_unavailable: bool = False,
            extra_hours_worked: int = 0,
            annual_leave_days: int = 28,
    ):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = f"{first_name} {last_name}"
        self.positions = positions
        self.cycle = cycle
        self.is_unavailable = is_unavailable
        self.extra_hours_worked = extra_hours_worked
        self.annual_leave_days = annual_leave_days

    def shifts_to_work(self, month: Month, off_days: int = 0, daily_norm: int = 8) -> int:
        month_working_hours = month.num_working_hours(daily_norm=daily_norm)
        hours_to_work = month_working_hours - \
                        self.extra_hours_worked - (off_days * daily_norm)
        shifts_to_work = math.ceil(hours_to_work / 12)
        return shifts_to_work

    def can_work_shift(self, shift, off_cycle=False):
        if off_cycle:
            return shift.position.sector.short_name in self.positions
        return self.cycle == shift.cycle and shift.position.sector.short_name in self.positions

    def __repr__(self) -> str:
        return f"{self.full_name} [C-{self.cycle}]"


class Shift:
    """
    A class used to represent a shift on a specific sector on a specific timeslot,
    that will eventually be assigned to a single nurse.

    """

    def __init__(
            self,
            timeslot: TimeSlot,
            position: Position,
            assigned_nurse: Nurse = None,
    ):
        self.timeslot = timeslot
        self.position = position
        self.assigned_nurse = assigned_nurse

    @property
    def id(self) -> int:
        return int(str(self.timeslot.id) + str(self.position.id).rjust(2, '0'))

    @property
    def cycle(self) -> int:
        return self.timeslot.cycle

    def is_on_same_timeslot(self, other) -> bool:
        if not isinstance(other, Shift):
            return NotImplemented
        return self.timeslot == other.timeslot

    def is_adjacent_shift(self, other) -> bool:
        if not isinstance(other, Shift):
            return NotImplemented
        return abs(self.id - other.id) == 1

    def get_timeslots_delta(self, other) -> int:
        if not isinstance(other, Shift):
            return NotImplemented
        return abs(self.id - other.id)

    def __eq__(self, other) -> bool:
        return (
                self.timeslot == other.timeslot
                and self.position == other.position
        )

    def __repr__(self) -> str:
        return f"{self.timeslot} {self.position.sector.short_name}"

    def __hash__(self):
        return hash((self.timeslot.day, self.timeslot.part, self.position))


class Schedule:
    def __init__(self, ss_manager: ScheduleSSManager):
        self.ss_manager = ss_manager
        self.year = ss_manager.year
        self.mnth = ss_manager.month
        self.working_days = self.month.working_days
        self.positions_per_timeslot = {str(ts): self.positions for ts in self.month.timeslots}
        self.schedule_matrix = [["" for _ in range(self.month.num_days * 2)] for n in range(100)]

    @cached_property
    def month(self):
        holidays_list = self.ss_manager.month_details[2]
        return Month(self.year, self.mnth, holidays_list)

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def nurses(self):
        nurses_matrix = self.ss_manager.nurse_list
        nurses = []
        for row in nurses_matrix:
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
                    Nurse(
                        id=nurse_id,
                        first_name=first_name,
                        last_name=last_name,
                        positions=sectors,
                        cycle=shift_cycle,
                        extra_hours_worked=extra_hours_worked,
                    )
                )
        return nurses

    @cached_property
    def available_nurses(self):
        return [n for n in self.nurses if n.cycle in [1, 2, 3, 4]]

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def sectors(self):
        sectors_matrix = self.ss_manager.sector_list
        sectors = []
        for row in sectors_matrix:
            if row[1] != "":
                sectors.append(
                    Sector(
                        id=int(row[0]),
                        short_name=row[2],
                        full_name=row[1],
                        min_nurses=int(row[3]),
                        optimal_nurses=int(row[4]),
                        max_nurses=int(row[5]),
                    )
                )
        return sectors

    @cached_property
    def nurses_lookup(self):
        return {n.id: n for n in self.nurses}

    @cached_property
    def sectors_lookup(self):
        return {s.id: s for s in self.sectors}

    @cached_property
    def sectors_lookup_by_name(self):
        return {s.short_name: s for s in self.sectors}

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def positions(self):
        positions_matrix = self.ss_manager.position_list
        positions = []
        for row in positions_matrix:
            if row[2] != "":
                id = int(row[0])
                name = row[2]
                sector = self.sectors_lookup_by_name[row[1]]
                positions.append(Position(id, name, sector))
        return positions

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def nurse_position_ranges(self):
        nurse_ranges_matrix = self.ss_manager.nurse_min_max
        filtered_sectors = dict(
            filter(lambda val: val[0] <= 13, self.sectors_lookup.items())
        )
        nurse_position_ranges = {}
        for row in nurse_ranges_matrix:
            if row[1] != "":
                nurse_id = int(row[0])
                nurse = self.nurses_lookup[nurse_id]
                if nurse not in nurse_position_ranges:
                    nurse_position_ranges[nurse] = {
                        filtered_sectors[s]: {"min": None, "max": None}
                        for s in filtered_sectors
                    }
                for s in range(len(filtered_sectors)):
                    sector = filtered_sectors[s + 1]
                    col = s * 2 + 2
                    if row[col] != "":
                        sector_min = int(row[col])
                        nurse_position_ranges[nurse][sector]["min"] = sector_min
                    if row[col + 1] != "":
                        sector_max = int(row[col + 1])
                        nurse_position_ranges[nurse][sector]["max"] = sector_max
        return nurse_position_ranges

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def rest_leave_days(self):
        rl_matrix = self.ss_manager.planned_rest_leaves
        rest_leave_days = {n: [] for n in self.nurses}
        for row in rl_matrix:
            if row[1] != "":
                nurse_id = int(row[0])
                nurse = self.nurses_lookup[nurse_id]
                for col in range(4, 49, 3):
                    if row[col] != "":
                        start_day = date.fromordinal(
                            date(1900, 1, 1).toordinal() + row[col] - 2
                        )
                        end_day = date.fromordinal(
                            date(1900, 1, 1).toordinal() + row[col + 1] - 2
                        )
                        day_count = (end_day - start_day).days + 1
                        for single_date in (
                                start_day + timedelta(n) for n in range(day_count)
                        ):
                            rest_leave_days[nurse].append(single_date)
        return rest_leave_days

    @cached_property
    def off_days(self):
        off_days = {n: [] for n in self.nurses}
        for nurse in self.rest_leave_days:
            if self.rest_leave_days[nurse]:
                for day in self.rest_leave_days[nurse]:
                    if day.month == self.month.month and day in self.working_days:
                        off_days[nurse].append(day)
        return off_days

    @cached_property
    def available_nurses_per_position_per_timeslot(self):
        positions = {s.short_name: None for s in self.sectors[:12]}
        nurses_per_position_per_timeslot = {}

        def filter_nurses_by_position(nurses, pos):
            return [n for n in nurses if pos in n.positions]

        for timeslot in self.month.timeslots:
            ts_nurses = self.available_nurses_per_timeslot[str(timeslot)]
            for pos in positions:
                nurses_per_position_per_timeslot[(str(timeslot), pos)] = filter_nurses_by_position(ts_nurses, pos)

        return nurses_per_position_per_timeslot

    @cached_property
    def timeslots_with_skill_deficit(self):
        def filter_sectors(sectors, threshold=3, exclude=('E', '8', '12', 'S')):
            return dict(filter(lambda s: len(s[1]) <= threshold and s[0] not in exclude, sectors.items()))

        timeslots_with_skill_deficit = {ts: filter_sectors(sector) for (ts, sector) in
                                        self.available_nurses_per_position_per_timeslot.items() if
                                        filter_sectors(sector)}

        return timeslots_with_skill_deficit

    @cached_property
    def unfillable_positions(self):
        unfillable_positions = {}

        def filter_unique_nurses(ts_dict):
            return set(reduce(lambda x, y: x + y, ts_dict.values()))

        for ts in self.timeslots_with_skill_deficit:
            timeslot = self.timeslots_with_skill_deficit[ts]
            positions = len(timeslot)
            nurses = len(filter_unique_nurses(timeslot))
            if nurses < positions:
                unfillable_positions[ts] = timeslot

        for ts in self.available_nurses_per_position_per_timeslot:
            for position in self.available_nurses_per_position_per_timeslot[ts]:
                if not self.available_nurses_per_position_per_timeslot[ts][position]:
                    unfillable_positions[ts] = position

        return unfillable_positions

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def shifts_to_work_per_nurse(self):
        shifts_to_work_per_nurse = {}
        for nurse in self.available_nurses:
            shifts_to_work_per_nurse[nurse] = nurse.shifts_to_work(
                self.month, off_days=len(self.off_days[nurse])
            )
        return shifts_to_work_per_nurse

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def shifts_to_work_per_cycle(self):
        shifts_to_work_per_cycle = {1: 0, 2: 0, 3: 0, 4: 0}
        for nurse in self.available_nurses:
            shifts_to_work_per_cycle[nurse.cycle] += self.shifts_to_work_per_nurse[nurse]
        return shifts_to_work_per_cycle

    @cached_property
    def updated_shifts_to_work_per_cycle(self):
        shifts_to_work_per_cycle = copy.deepcopy(self.shifts_to_work_per_cycle)
        for nurse in self.nurses_with_not_enough_cycle_timeslots:
            shifts_to_work_per_cycle[nurse.cycle] -= self.nurses_with_not_enough_cycle_timeslots[nurse][
                'extra_timeslots_needed']
        return shifts_to_work_per_cycle

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def available_nurses_per_timeslot(self):
        the_nurses_per_timeslot = {str(ts): [] for ts in self.month.timeslots}
        for ts in self.month.timeslots:
            for nurse in self.available_nurses:
                if nurse.cycle == ts.cycle and not ts.overlaps_with(self.rest_leave_days[nurse]):
                    the_nurses_per_timeslot[str(ts)].append(nurse)
        return the_nurses_per_timeslot

    @cached_property
    def available_timeslots_per_nurse(self):
        available_timeslots_per_nurse = {n: [] for n in self.available_nurses}
        for nurse in self.available_nurses:
            for timeslot in self.month.timeslots:
                if nurse in self.available_nurses_per_timeslot[str(timeslot)]:
                    available_timeslots_per_nurse[nurse].append(timeslot)
        return available_timeslots_per_nurse

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def nurses_with_not_enough_cycle_timeslots(self):
        nurses = {}
        for nurse in self.available_nurses:
            if self.shifts_to_work_per_nurse[nurse] > len(self.available_timeslots_per_nurse[nurse]):
                nurses[nurse] = {}
                nurses[nurse]['extra_timeslots_needed'] = self.shifts_to_work_per_nurse[nurse] - \
                                                          len(self.available_timeslots_per_nurse[nurse])
        return nurses

    @cached_property
    def timeslots_ordered_by_num_nurses(self):
        timeslots = []
        for ts in self.month.timeslots:
            ts_nurses = self.initial_nurses_per_timeslot[str(ts)]["num_nurses"]
            timeslots.append([ts, ts_nurses])

        return sorted(timeslots, key=lambda t: (t[1], t[0].part))

    @cached_property
    def possible_extra_ts_for_nurses_with_ts_deficit(self):
        nurses_with_not_enough_cycle_timeslots = self.nurses_with_not_enough_cycle_timeslots
        off_cycle_ts = {1: [(2, 1), (3, 2)], 2: [(4, 1), (1, 2)], 3: [
            (1, 1), (4, 2)], 4: [(3, 1), (2, 2)]}
        possible_extra_timeslots_per_nurse = {}
        for nurse in nurses_with_not_enough_cycle_timeslots:
            possible_extra_timeslots = []
            for timeslot in self.month.timeslots:
                for i in range(2):
                    if timeslot.cycle == off_cycle_ts[nurse.cycle][i][0] and timeslot.part == \
                            off_cycle_ts[nurse.cycle][i][1] and timeslot.day not in self.rest_leave_days[
                        nurse] and not (
                            timeslot.part == 2 and timeslot.day + timedelta(days=1) in self.rest_leave_days[nurse]):
                        possible_extra_timeslots.append(timeslot)
            possible_extra_timeslots_per_nurse[nurse] = possible_extra_timeslots
        return possible_extra_timeslots_per_nurse

    @cached_property
    def extra_ts_for_nurses_with_ts_deficit(self):
        possible_extra_timeslots_per_nurse = self.possible_extra_ts_for_nurses_with_ts_deficit
        timeslots_ordered_by_num_nurses = copy.deepcopy(
            self.timeslots_ordered_by_num_nurses)
        selected_ts_per_nurse = {n: [] for n in self.nurses_with_not_enough_cycle_timeslots}
        for nurse in self.nurses_with_not_enough_cycle_timeslots:
            for i in range(self.nurses_with_not_enough_cycle_timeslots[nurse]['extra_timeslots_needed']):
                for timeslot in timeslots_ordered_by_num_nurses:
                    if timeslot[0] in possible_extra_timeslots_per_nurse[nurse]:
                        selected_ts_per_nurse[nurse].append(timeslot[0])
                        timeslot[1] += 1
                        timeslots_ordered_by_num_nurses.sort(
                            key=lambda t: (t[1], t[0].part))
                        break
        return selected_ts_per_nurse

    @cached_property
    @TimerLog(logger_name='scheduler.models')
    def initial_nurses_per_timeslot(self):
        cycle_details = {}
        for cycle in [1, 2, 3, 4]:
            cycle_timeslots = self.month.timeslots_per_cycle[cycle]
            cycle_shifts_to_work = self.updated_shifts_to_work_per_cycle[cycle]
            avg_nurses_per_ts, rest_nurses = divmod(
                cycle_shifts_to_work, len(cycle_timeslots))
            cycle_details[cycle] = {
                "timeslots": cycle_timeslots,
                "avg_nurses_per_ts": avg_nurses_per_ts,
                "rest_nurses": rest_nurses,
                "shifts_to_work": cycle_shifts_to_work,
                "phase_1_nurses": 0,
            }

        nurses_per_timeslot = {}

        # * Phase 1 nurse distribution
        for ts in self.month.timeslots:
            available_nurses = len(self.available_nurses_per_timeslot[str(ts)])
            avg_nurses_per_ts = cycle_details[ts.cycle]["avg_nurses_per_ts"]
            num_nurses = min(available_nurses, avg_nurses_per_ts)

            if available_nurses <= avg_nurses_per_ts:
                nurses_per_timeslot[str(ts)] = {
                    "num_nurses": num_nurses,
                    "flag": "max_available",
                    "timeslot": ts,
                    "cycle": ts.cycle,
                    "str": str(ts)
                }
            else:
                nurses_per_timeslot[str(ts)] = {
                    "num_nurses": num_nurses,
                    "flag": "avg_nurses_per_ts",
                    "timeslot": ts,
                    "cycle": ts.cycle,
                    "str": str(ts)
                }
            cycle_details[ts.cycle]["phase_1_nurses"] += num_nurses

        # * Set number of unplanned shiftslots after phase 1 nurse distribution
        for cycle in cycle_details:
            cycle_details[cycle]["unplanned_shiftslots"] = (
                    cycle_details[cycle]["shifts_to_work"]
                    - cycle_details[cycle]["phase_1_nurses"]
            )

        # * Phase 2 nurse distribution
        for cycle in [1, 2, 3, 4]:
            while cycle_details[cycle]["unplanned_shiftslots"] > 0:
                for ts in nurses_per_timeslot:
                    available_nurses = len(self.available_nurses_per_timeslot[ts])
                    ts_nurses = nurses_per_timeslot[ts]["num_nurses"]
                    if available_nurses <= ts_nurses:
                        nurses_per_timeslot[ts]["flag"] = "max_available"

                # * Get updated list of timeslots with available nurses
                ts_wth_avail_nurses = [
                    nurses_per_timeslot[ts]
                    for ts in nurses_per_timeslot
                    if nurses_per_timeslot[ts]["flag"] != "max_available"
                       and nurses_per_timeslot[ts]["cycle"] == cycle
                ]

                # * Get min number of nurses per timeslot from timeslots with available nurses
                min_nurses_per_ts = sorted(ts_wth_avail_nurses, key=lambda ts: ts["num_nurses"])[
                    0]["num_nurses"]

                # * Get all timeslots with min number of nurses and available nurses
                ts_with_min_nurses = [
                    ts for ts in ts_wth_avail_nurses
                    if ts["num_nurses"] == min_nurses_per_ts
                ]

                # * Create weights to preferably add more nurses to day timeslots
                weights = [6 if ts["timeslot"].part ==
                                1 else 1 for ts in ts_with_min_nurses]

                # * Randomly pick a timeslot for adding a nurse based on above weights
                random_ts = random.choices(
                    ts_with_min_nurses, weights=weights)[0]

                # * Update nurses_per_timeslot dict by adding 1 to the number of nurses on the randomly picked timeslot
                nurses_per_timeslot[random_ts["str"]]["num_nurses"] += 1

                # * Subtract 1 from the number of unplanned shiftslots
                cycle_details[cycle]["unplanned_shiftslots"] -= 1

        return nurses_per_timeslot

    @cached_property
    def updated_nurses_per_timeslot(self):
        nurses_per_timeslot = copy.deepcopy(self.initial_nurses_per_timeslot)

        # * Add extra shifts for nurses who don't have enough timeslots on their cycle timeslots
        extra_shiftslots = self.extra_ts_for_nurses_with_ts_deficit
        for nurse in extra_shiftslots:
            for timeslot in extra_shiftslots[nurse]:
                nurses_per_timeslot[str(timeslot)]['num_nurses'] += 1
                nurses_per_timeslot[str(timeslot)]['flag'] += ' + 1 off cycle'

        return nurses_per_timeslot

    @cached_property
    def all_shifts(self):
        all_shifts = {str(ts): [] for ts in self.month.timeslots}
        nurses_per_timeslot = self.updated_nurses_per_timeslot

        for ts in self.month.timeslots:
            ts_positions = nurses_per_timeslot[str(ts)]["num_nurses"]
            for position in self.positions[:ts_positions]:
                shift = Shift(ts, position)
                all_shifts[str(ts)].append(shift)

        return all_shifts

    @cached_property
    def fixed_assignments(self):
        fixed_assignments = []
        for row in self.ss_manager.fixed_assignments:
            if row[1] != "":
                nurse_id = int(row[0])
                nurse = self.nurses_lookup[nurse_id]
                for col in range(3, self.month.num_days * 2 + 3):
                    if row[col] != "":
                        day = date(self.month.year,
                                   self.month.month, (col - 1) // 2)
                        part = (col + 1) % 2 + 1
                        ts = TimeSlot(day, part)
                        for pos in self.positions_per_timeslot[str(ts)]:
                            if pos.sector.short_name == row[col]:
                                position = pos
                                shift = Shift(ts, position, nurse)
                                fixed_assignments.append(shift)
                                break
        return fixed_assignments

    def _add_shifts_to_schedule_matrix(self, solution_dict):
        for nurse in solution_dict:
            row = nurse.id - 1
            for shift in solution_dict[nurse]:
                col = int(shift.timeslot.day.day) * 2 - 3 + shift.timeslot.part
                self.schedule_matrix[row][col] = shift.position.sector.short_name

    def _add_rest_leaves_to_schedule_matrix(self):
        for nurse in self.off_days:
            if self.off_days[nurse]:
                row = nurse.id - 1
                for day in self.off_days[nurse]:
                    col = int(day.day) * 2 - 2
                    self.schedule_matrix[row][col] = "CO"

    def _add_sick_leaves_to_schedule_matrix(self):
        for nurse in self.nurses:
            if nurse.cycle == "CB":
                row = nurse.id - 1
                for day in self.working_days:
                    col = int(day.day) * 2 - 2
                    self.schedule_matrix[row][col] = "CB"

    def _add_maternity_leaves_to_schedule_matrix(self):
        for nurse in self.nurses:
            if nurse.cycle == "Ma":
                row = nurse.id - 1
                for day in self.working_days:
                    col = int(day.day) * 2 - 2
                    self.schedule_matrix[row][col] = "Ma"

    @cached_property
    def monthly_planned_hours(self):
        nurse_hours = {
            n: {"worked_hours": 0, "off_work_paid_hours": 0} for n in self.nurses
        }
        for nurse_id, row in enumerate(self.schedule_matrix[: len(self.nurses)]):
            nurse = self.nurses_lookup[nurse_id + 1]
            for col in range(len(row)):
                if row[col] != "":
                    if row[col] in [s.short_name for s in self.sectors[:13]] or row[
                        col
                    ] in [12, "12"]:
                        nurse_hours[nurse]["worked_hours"] += 12
                    elif row[col] in [8, "8"]:
                        nurse_hours[nurse]["worked_hours"] += 8
                    elif row[col] in ["CO", "CB", "Obl", "Ma", "IZ"]:
                        nurse_hours[nurse]["off_work_paid_hours"] += 8
        return nurse_hours

    def _add_recovery_days_to_schedule_matrix(self):
        hours_to_work = self.month.num_working_days * 8
        extra_hours = {
            n: {"extra_hours_worked": n.extra_hours_worked, "hours_deficit": 0}
            for n in self.nurses
        }
        for nurse in self.nurses:
            nurse_planned_hours = (
                    self.monthly_planned_hours[nurse]["worked_hours"]
                    + self.monthly_planned_hours[nurse]["off_work_paid_hours"]
            )
            if nurse_planned_hours < hours_to_work:
                extra_hours[nurse]["hours_deficit"] += (
                        hours_to_work - nurse_planned_hours
                )
        for nurse in extra_hours:
            if (
                    extra_hours[nurse]["extra_hours_worked"] > 0
                    and extra_hours[nurse]["extra_hours_worked"]
                    >= extra_hours[nurse]["hours_deficit"]
            ):
                recovery_hours = extra_hours[nurse]["hours_deficit"]
                recovery_days = math.ceil(recovery_hours / 8)
                non_working_days = [
                    int(d.day) * 2 - 2 for d in self.month.working_days]
                available_days = []
                for col in non_working_days:
                    if (
                            self.schedule_matrix[nurse.id - 1][col] == ""
                            and self.schedule_matrix[nurse.id - 1][col - 1] == ""
                            and self.schedule_matrix[nurse.id - 1][col + 1] == ""
                    ):
                        available_days.append(col)
                random_days = random.sample(available_days, recovery_days)
                for day in random_days:
                    self.schedule_matrix[nurse.id - 1][day] = "R"
                extra_hours[nurse]["recovered_hours"] = recovery_hours

    @TimerLog(logger_name='scheduler.models')
    def create_schedule_matrix(self, solution_dict):
        self._add_shifts_to_schedule_matrix(solution_dict)
        self._add_rest_leaves_to_schedule_matrix()
        self._add_sick_leaves_to_schedule_matrix()
        self._add_maternity_leaves_to_schedule_matrix()
        self._add_recovery_days_to_schedule_matrix()
        return self.schedule_matrix

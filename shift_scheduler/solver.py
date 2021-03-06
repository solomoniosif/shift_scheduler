from functools import cached_property
from ortools.sat.python import cp_model

try:
    from shift_scheduler.utils import TimerLog
    from shift_scheduler import models
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))

    from shift_scheduler.utils import TimerLog
    from shift_scheduler import models


class ScheduleModel(cp_model.CpModel):
    """
    A class that extends ORTools CP Model.
    It contains methods to add shift variables, and constraints.

    An instance of this class will be passed to the
    ORTools CP Solver that will try to find
    an optimal solution for scheduling nurse shifts
    with the given constraints.
    """

    def __init__(self, schedule: models.Schedule):
        super().__init__()
        self.schedule = schedule
        self.variables = self._create_shift_variables()
        self._add_constraints()

    def _create_shift_variables(self) -> dict[tuple[int, int, int], cp_model.IntVar]:
        variables = {}
        for nurse in self.schedule.available_nurses:
            for timeslot in self.schedule.month.timeslots:
                for shift in self.schedule.all_shifts[str(timeslot)]:
                    if nurse.can_work_shift(shift) and not timeslot.overlaps_with(self.schedule.rest_leave_days[nurse]):
                        variables[(nurse.id, timeslot.id, shift.id)] = self.NewBoolVar(
                            f"{timeslot} | {nurse} works on {shift.position.sector.short_name}")

        extra_timeslots = self.schedule.extra_ts_for_nurses_with_ts_deficit
        for nurse in extra_timeslots:
            for timeslot in extra_timeslots[nurse]:
                for shift in self.schedule.all_shifts[str(timeslot)]:
                    if nurse.can_work_shift(shift, off_cycle=True):
                        variables[(nurse.id, timeslot.id, shift.id)] = self.NewBoolVar(
                            f"{timeslot} | {nurse} works on {shift.position.sector.short_name}")

        for shift in self.schedule.fixed_assignments:
            if (shift.assigned_nurse.id, shift.timeslot.id, shift.id) not in variables:
                variables[(shift.assigned_nurse.id, shift.timeslot.id, shift.id)] = self.NewBoolVar(
                    f"{shift.timeslot} | {shift.assigned_nurse} works on {shift.position.sector.short_name}")

        return variables

    def _add_fixed_assignment(self) -> None:
        for shift in self.schedule.fixed_assignments:
            self.Add(self.variables[(shift.assigned_nurse.id, shift.timeslot.id, shift.id)] == 1)

    def _add_no_double_assignment(self) -> None:
        for timeslot in self.schedule.month.timeslots:
            for shift in self.schedule.all_shifts[str(timeslot)]:
                self.Add(
                    sum(
                        [self.variables[(nurse.id, timeslot.id, shift.id)]
                         for nurse in self.schedule.available_nurses
                         if (nurse.id, timeslot.id, shift.id) in self.variables]
                    ) == 1
                )

    def _add_single_shift_per_timeslot(self) -> None:
        for nurse in self.schedule.available_nurses:
            for timeslot in self.schedule.month.timeslots:
                self.Add(
                    sum(
                        self.variables[(nurse.id, timeslot.id, shift.id)]
                        for shift in self.schedule.all_shifts[str(timeslot)]
                        if (nurse.id, timeslot.id, shift.id) in self.variables
                    ) <= 1
                )

    @TimerLog(logger_name='scheduler.solver')
    def _add_number_of_shifts_per_nurse(self) -> None:
        nurses_with_not_enough_cycle_timeslots = self.schedule.nurses_with_not_enough_cycle_timeslots
        for nurse in self.schedule.available_nurses:
            if nurse not in nurses_with_not_enough_cycle_timeslots:
                shifts_to_work = self.schedule.shifts_to_work_per_nurse[nurse]
                planned_shifts = [
                    self.variables[(nurse.id, timeslot.id, shift.id)]
                    for timeslot in self.schedule.month.timeslots
                    for shift in self.schedule.all_shifts[str(timeslot)]
                    if (nurse.id, timeslot.id, shift.id) in self.variables
                ]
                self.Add(sum(planned_shifts) == shifts_to_work)

    @TimerLog(logger_name='scheduler.solver')
    def _add_min_positions(self) -> None:
        def add_min_nurse_position(nurse, sector, min_shifts):
            planned_shifts = []
            for timeslot in self.schedule.month.timeslots:
                for shift in self.schedule.all_shifts[str(timeslot)]:
                    if (nurse.id, timeslot.id, shift.id) in self.variables and shift.position.sector == sector:
                        planned_shifts.append(self.variables[(nurse.id, timeslot.id, shift.id)])
            self.Add(sum(planned_shifts) >= min_shifts)

        for nurse in self.schedule.nurse_position_ranges:
            for sector in self.schedule.nurse_position_ranges[nurse]:
                min_shifts = self.schedule.nurse_position_ranges[nurse][sector]['min']
                if min_shifts is not None:
                    add_min_nurse_position(nurse, sector, min_shifts)

    @TimerLog(logger_name='scheduler.solver')
    def _add_max_positions(self) -> None:
        def add_max_nurse_position(nurse, sector, max_shifts):
            planned_shifts = []
            for timeslot in self.schedule.month.timeslots:
                for shift in self.schedule.all_shifts[str(timeslot)]:
                    if (nurse.id, timeslot.id, shift.id) in self.variables and shift.position.sector == sector:
                        planned_shifts.append(self.variables[(nurse.id, timeslot.id, shift.id)])
            self.Add(sum(planned_shifts) <= max_shifts)

        for nurse in self.schedule.nurse_position_ranges:
            for sector in self.schedule.nurse_position_ranges[nurse]:
                max_shifts = self.schedule.nurse_position_ranges[nurse][sector]['max']
                if max_shifts is not None:
                    add_max_nurse_position(nurse, sector, max_shifts)

    def _maximize_positions_per_nurse(self) -> None:
        for nurse in self.schedule.available_nurses:
            nurse_positions = []
            for timeslot in self.schedule.month.timeslots:
                for shift in self.schedule.all_shifts[str(timeslot)]:
                    if (nurse.id, timeslot.id, shift.id) in self.variables:
                        nurse_positions.append(shift.position.sector)
            self.Maximize(sum([16 - nurse_positions.count(el) for el in list(set(nurse_positions))]))

    @TimerLog(logger_name='scheduler.solver')
    def _add_constraints(self) -> None:
        self._add_fixed_assignment()
        self._add_no_double_assignment()
        self._add_single_shift_per_timeslot()
        self._add_number_of_shifts_per_nurse()
        self._add_min_positions()
        self._add_max_positions()
        self._maximize_positions_per_nurse()


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables: dict[tuple[int, int, int], cp_model.IntVar], schedule: models.Schedule):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.variables = variables
        self.schedule = schedule
        self.nurses = self.schedule.available_nurses
        self.timeslots = self.schedule.month.timeslots
        self.shifts = self.schedule.all_shifts
        self.solution = {}

    @TimerLog(logger_name='scheduler.solver')
    def on_solution_callback(self) -> None:
        for t in self.timeslots:
            for n in self.nurses:
                for s in self.shifts[str(t)]:
                    if (n.id, t.id, s.id) in self.variables and self.Value(
                            self.variables[(n.id, t.id, s.id)]
                    ):
                        s.nurse = n
                        if n in self.solution:
                            self.solution[n].append(s)
                        else:
                            self.solution[n] = [s]

    @cached_property
    def solution_by_timeslot(self) -> dict[models.TimeSlot, list[models.Shift]]:
        solution_by_timeslot = {ts: [] for ts in self.timeslots}
        for nurse in self.solution:
            for shift in self.solution[nurse]:
                solution_by_timeslot[shift.timeslot].append(shift)
        return solution_by_timeslot


class NurseCycleDistributionModel(cp_model.CpModel):

    def __init__(self, schedule: models.Schedule):
        super().__init__()
        self.schedule = schedule
        self.variables = self._create_variables()
        self._add_constraints()

    def _create_variables(self) -> dict[tuple[int, int], cp_model.IntVar]:
        variables = {}
        for nurse in self.schedule.available_nurses:
            for cycle in [1, 2, 3, 4]:
                variables[(nurse.id, cycle)] = self.NewBoolVar(f"{nurse} works on cycle {cycle}")
        return variables

    def _add_each_nurse_is_assigned_to_one_cycle(self) -> None:
        for nurse in self.schedule.available_nurses:
            self.Add(sum([self.variables[nurse.id, cycle] for cycle in [1, 2, 3, 4]]) == 1)

    def _add_distribute_nurses_evenly(self) -> None:
        min_nurses_per_cycle = len(self.schedule.available_nurses) // 4
        for cycle in [1, 2, 3, 4]:
            self.Add(sum([self.variables[nurse.id, cycle] for nurse in
                          self.schedule.available_nurses]) >= min_nurses_per_cycle)
            # self.Add(sum([self.variables[nurse.id, cycle] for nurse in
            #               self.schedule.available_nurses]) <= min_nurses_per_cycle + 1)

    def _add_distribute_nurses_evenly_by_skills(self) -> None:
        for sector in self.schedule.essential_sectors:
            for cycle in [1, 2, 3, 4]:
                min_nurses_per_cycle = len(self.schedule.available_nurses_per_sector[sector.short_name]) // 4
                self.Add(sum([self.variables[n.id, cycle] for n in self.schedule.available_nurses if
                              sector.short_name in n.positions]) >= min_nurses_per_cycle)
        for nurse in self.schedule.nurses_with_7_positions:
            for cycle in [1, 2, 3, 4]:
                min_nurses_per_cycle = len(self.schedule.nurses_with_7_positions) // 4
                self.Add(sum([self.variables[n.id, cycle] for n in
                              self.schedule.nurses_with_7_positions]) >= min_nurses_per_cycle)

    def _add_constraints(self) -> None:
        self._add_each_nurse_is_assigned_to_one_cycle()
        self._add_distribute_nurses_evenly()
        self._add_distribute_nurses_evenly_by_skills()


class NurseDistributionSolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables: dict[tuple[int, int], cp_model.IntVar], schedule: models.Schedule):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.variables = variables
        self.schedule = schedule
        self.solution = {1: [], 2: [], 3: [], 4: []}

    def on_solution_callback(self):
        for n in self.schedule.available_nurses:
            for c in [1, 2, 3, 4]:
                if self.Value(self.variables[n.id, c]):
                    self.solution[c].append(n)

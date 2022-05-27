from datetime import timedelta
import logging
from ortools.sat.python import cp_model

from utils import TimerLog


class ScheduleModel(cp_model.CpModel):
    """
    A class that extends ORTools CP Model.
    It contains methods to add shift variables, and constraints.

    An instance of this class will be passed to the
    ORTools CP Solver that will try to find
    an optimal solution for scheduling nurse shifts
    with the given constraints.
    """

    def __init__(self, schedule):
        super().__init__()
        self.schedule = schedule
        self.variables = self._create_shift_variables()
        self._add_constraints()

    @TimerLog(logger_name='scheduler.solver')
    def _create_shift_variables(self):
        variables = {}
        for n, nurse in enumerate(self.schedule.available_nurses):
            for t, timeslot in enumerate(self.schedule.month.timeslots):
                for s, shift in enumerate(self.schedule.all_shifts[str(timeslot)]):
                    if nurse.can_work_shift(shift) and not timeslot.overlaps_with(self.schedule.rest_leave_days[nurse]):
                        variables[(n, t, s)] = self.NewBoolVar(
                            f"{timeslot} | {nurse} works on {shift.position.sector.short_name}")

        extra_ts = self.schedule.extra_ts_for_nurses_with_ts_deficit
        for n, nurse in enumerate(self.schedule.available_nurses):
            if nurse in extra_ts:
                for t, timeslot in enumerate(self.schedule.month.timeslots):
                    if timeslot in extra_ts[nurse]:
                        for s, shift in enumerate(self.schedule.all_shifts[str(timeslot)]):
                            if nurse.can_work_shift(shift, off_cycle=True):
                                variables[(n, t, s)] = self.NewBoolVar(
                                    f"{timeslot} | {nurse} works on {shift.position.sector.short_name}")
        return variables

    def _add_no_double_assignment(self):
        for t, timeslot in enumerate(self.schedule.month.timeslots):
            for s, shift in enumerate(self.schedule.all_shifts[str(timeslot)]):
                self.Add(
                    sum(
                        [self.variables[(n, t, s)]
                         for n, nurse in enumerate(self.schedule.available_nurses)
                         if (n, t, s) in self.variables]
                    ) == 1
                )

    def _add_single_shift_per_timeslot(self):
        for n, nurse in enumerate(self.schedule.available_nurses):
            for t, timeslot in enumerate(self.schedule.month.timeslots):
                self.Add(
                    sum(
                        self.variables[(n, t, s)]
                        for s, shift in enumerate(self.schedule.all_shifts[str(timeslot)])
                        if (n, t, s) in self.variables
                    ) <= 1
                )

    def _add_number_of_shifts_per_nurse(self):
        nurses_with_not_enough_cycle_timeslots = self.schedule.nurses_with_not_enough_cycle_timeslots
        for n, nurse in enumerate(self.schedule.available_nurses):
            if nurse not in nurses_with_not_enough_cycle_timeslots:
                shifts_to_work = self.schedule.shifts_to_work_per_nurse[nurse]
                planned_shifts = [
                    self.variables[(n, t, s)]
                    for t, timeslot in enumerate(self.schedule.month.timeslots)
                    for s, shift in enumerate(self.schedule.all_shifts[str(timeslot)])
                    if (n, t, s) in self.variables
                ]
                self.Add(sum(planned_shifts) == shifts_to_work)

    @TimerLog(logger_name='scheduler.solver')
    def _add_constraints(self):
        self._add_no_double_assignment()
        self._add_single_shift_per_timeslot()
        self._add_number_of_shifts_per_nurse()


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, schedule):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.variables = variables
        self.schedule = schedule
        self.nurses = self.schedule.available_nurses
        self.timeslots = self.schedule.month.timeslots
        self.shifts = self.schedule.all_shifts
        self.solution = {}

    @TimerLog(logger_name='scheduler.solver')
    def on_solution_callback(self):
        for t, timeslot in enumerate(self.timeslots):
            for n, nurse in enumerate(self.nurses):
                for s, shift in enumerate(self.shifts[str(timeslot)]):
                    if (n, t, s) in self.variables and self.Value(
                            self.variables[(n, t, s)]
                    ):
                        shift.nurse = nurse
                        if nurse in self.solution:
                            self.solution[nurse].append(shift)
                        else:
                            self.solution[nurse] = [shift]

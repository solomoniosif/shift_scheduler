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

    def _create_shift_variables(self):
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
        return variables

    def _add_no_double_assignment(self):
        for timeslot in self.schedule.month.timeslots:
            for shift in self.schedule.all_shifts[str(timeslot)]:
                self.Add(
                    sum(
                        [self.variables[(nurse.id, timeslot.id, shift.id)]
                         for nurse in self.schedule.available_nurses
                         if (nurse.id, timeslot.id, shift.id) in self.variables]
                    ) == 1
                )

    def _add_single_shift_per_timeslot(self):
        for nurse in self.schedule.available_nurses:
            for timeslot in self.schedule.month.timeslots:
                self.Add(
                    sum(
                        self.variables[(nurse.id, timeslot.id, shift.id)]
                        for shift in self.schedule.all_shifts[str(timeslot)]
                        if (nurse.id, timeslot.id, shift.id) in self.variables
                    ) <= 1
                )

    def _add_number_of_shifts_per_nurse(self):
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

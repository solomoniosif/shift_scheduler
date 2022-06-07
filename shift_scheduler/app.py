import logging

from ortools.sat.python import cp_model

from interface import ScheduleSSManager
from models import Month, Schedule
from solver import ScheduleModel, SolutionCollector
from utils import CustomFormatter, TimerLog

logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
console.setFormatter(CustomFormatter())
logger.addHandler(console)
app_logger = logging.getLogger('scheduler.app')


@TimerLog(logger_name='scheduler.app', text="Schedule generation")
def main():
    year, mnth = 2022, 5
    app_logger.info('Working on a schedule solution for month %s %s', Month.MONTH_NAMES[mnth - 1], year)

    ss_manager = ScheduleSSManager(year, mnth)
    this_month_ss = ss_manager.get_or_create_new_ss()
    schedule = Schedule(ss_manager)
    model = ScheduleModel(schedule)

    solver = cp_model.CpSolver()
    solution_printer = SolutionCollector(model.variables, schedule)

    status = solver.Solve(model, solution_printer)

    app_logger.debug("Solution status: %s", solver.StatusName())

    response_stats = solver.ResponseStats()

    solution = solution_printer.solution

    ss_manager.insert_shifts(schedule.create_schedule_matrix(solution))


if __name__ == '__main__':
    main()

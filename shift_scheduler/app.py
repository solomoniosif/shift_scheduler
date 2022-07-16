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
def main() -> None:
    # Get year and month from user input
    year = int(input("Enter the year: "))
    while year not in range(2021, 2051):
        year = int(input("Entered year must be between 2021 and 2050. \nPlease provide a year in this range: "))
    month = int(input("Enter the month (1 to 12): "))
    while month not in range(1, 13):
        month = int(input("Entered month must be between 1 and 12. \nPlease provide a month in this range: "))

    # Log to console the start of schedule generation
    app_logger.info('Working on a schedule solution for month %s %s', Month.MONTH_NAMES[month - 1], year)

    # Initialize models for given month
    ss_manager = ScheduleSSManager(year, month)
    this_month_ss = ss_manager.get_or_create_new_ss()
    schedule = Schedule(ss_manager)

    # Create the model
    model = ScheduleModel(schedule)

    # Initialize CP-SAT Solver and the solution callback instance
    solver = cp_model.CpSolver()
    solution_collector = SolutionCollector(model.variables, schedule)

    # Search for a feasible solution and save it to a variable
    status = solver.Solve(model, solution_collector)
    solution = solution_collector.solution

    # Log solver status to console
    app_logger.debug("Solution status: %s", solver.StatusName())

    # Insert solution into target spreadsheet
    if solver.StatusName() in ['OPTIMAL', 'FEASIBLE']:
        ss_manager.insert_shifts(schedule.create_schedule_matrix(solution))


if __name__ == '__main__':
    main()

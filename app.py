import logging
import time

from ortools.sat.python import cp_model

from interface import ScheduleSSManager
from models import Month, Schedule
from solver import ScheduleModel, SolutionCollector
from utils import CustomFormatter

logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
console.setFormatter(CustomFormatter())
logger.addHandler(console)
app_logger = logging.getLogger('scheduler.app')

start_time = time.time()
year, mnth = 2022, 4
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

# ss_manager.insert_shifts(schedule.create_schedule_matrix(solution))

end_time = time.time()
elapsed_time = end_time - start_time
if solver.StatusName() == 'OPTIMAL':
    app_logger.info('Schedule generation for month %s took %s seconds', Month.MONTH_NAMES[mnth - 1],
                    round(elapsed_time, 2))

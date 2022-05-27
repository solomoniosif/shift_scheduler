import functools
import logging
import time

import colorama
from colorama import Fore

colorama.init(autoreset=True)


class TimerError(Exception):
    """A custom exception used to report errors in use of TimerLog class"""
    pass


class TimerLog:

    def __init__(self, logger_name, name=None):
        self.logger_name = logger_name
        self.logger = logging.getLogger(self.logger_name)
        self.name = name
        self._start_time = None

    def start(self):
        if self._start_time is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it")

        self._start_time = time.perf_counter()

    def stop(self):
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        if self.logger:
            self.logger.debug(
                Fore.WHITE + 'Function ' + Fore.GREEN + '%s ' + Fore.WHITE + 'executed in' +
                Fore.LIGHTRED_EX + ' %s ' + Fore.WHITE + 'seconds',
                self.name, round(elapsed_time, 2))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc_info):
        self.stop()

    def __call__(self, func):
        if not self.name:
            self.name = func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    blue = "\x1b[34m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    bold = "\x1b[1m"
    bright_green = "\x1b[32m"
    white = "\x1b[37m"
    underline = "\x1b[4m"
    reversed = "\x1b[7m"
    reset = "\x1b[0m"
    format = "%(asctime)s\t%(name)s   \t%(message)s"

    FORMATS = {
        'scheduler.app': bright_green + format + reset,
        'scheduler.interface': yellow + format + reset,
        'scheduler.models': red + format + reset,
        'scheduler.solver': blue + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.name)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

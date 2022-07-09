import calendar
import secrets
from datetime import date, datetime
from functools import cached_property
from typing import List, Tuple

import pygsheets
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

try:
    from shift_scheduler import secrets
    from shift_scheduler.utils import TimerLog
except ImportError:
    import sys
    from pathlib import Path

    root_folder = Path(__file__).parent.parent.absolute()
    sys.path.append(str(root_folder))
    from shift_scheduler import secrets
    from shift_scheduler.utils import TimerLog


class ScheduleSSManager:
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
    COLS = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        "AA",
        "AB",
        "AC",
        "AD",
        "AE",
        "AF",
        "AG",
        "AH",
        "AI",
        "AJ",
        "AK",
        "AL",
        "AM",
        "AN",
        "AO",
        "AP",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AV",
        "AW",
        "AX",
        "AY",
        "AZ",
        "BA",
        "BB",
        "BC",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BK",
        "BL",
        "BM",
        "BN",
        "BO",
        "BP",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BU",
        "BV",
        "BW",
        "BX",
        "BY",
        "BZ",
    ]

    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.month_name = ScheduleSSManager.MONTH_NAMES[self.month - 1]
        self.client = pygsheets.authorize(
            service_account_file=secrets.PATH_TO_SERVICE_ACCOUNT_FILE
        )
        self.this_month_ss = None

    @cached_property
    def model_ss(self) -> pygsheets.Spreadsheet:
        return self.client.open_by_key(secrets.MODEL_SS_KEY)

    @cached_property
    def settings_ss(self) -> pygsheets.Spreadsheet:
        return self.client.open_by_key(secrets.SETTINGS_SS_KEY)

    def _create_new_ss_from_model(self) -> None:
        g_auth = GoogleAuth()
        g_auth.LocalWebserverAuth()
        drive = GoogleDrive(g_auth)
        source_ss = self.model_ss
        source_ss_id = source_ss.id

        source = drive.CreateFile({"id": source_ss_id})
        source.FetchMetadata("title")
        dest_title = f"Planificator AM {self.month_name} {self.year}"

        copied_file = {"title": dest_title}
        f = (
            drive.auth.service.files()
                .copy(fileId=source_ss_id, body=copied_file)
                .execute()
        )

        new_ss = drive.CreateFile({"id": f["id"]})
        permission = new_ss.InsertPermission(
            {
                "type": "user",
                "value": secrets.SERVICE_ACCOUNT_EMAIL,
                "role": "writer",
            }
        )

        new_ss.FetchMetadata("alternateLink")
        new_ss_link = new_ss["alternateLink"]
        new_ss_id = new_ss_link.split("/")[5]

        if not self.this_month_ss:
            self.this_month_ss = self.client.open_by_key(new_ss_id)

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def holiday_list(self) -> List[date]:
        ro_holidays_raw = self.settings_ss.worksheet_by_title("Sarbatori legale").range(
            "C3:C212", returnas="matrix"
        )
        return [
            datetime.strptime(d[0], "%m/%d/%Y").date()
            for d in ro_holidays_raw
            if d[0] != ""
        ]

    @cached_property
    def non_working_days(self) -> List[date]:
        non_working_days = []
        _, month_days = calendar.monthrange(self.year, self.month)
        for d in range(1, month_days + 1):
            day = date(self.year, self.month, d)
            if day.weekday() >= 5 or day in self.holiday_list:
                non_working_days.append(day)
        return non_working_days

    def _configure_ss(self) -> None:
        first_dom, month_days = calendar.monthrange(self.year, self.month)
        weekday_names = ["Lu", "Ma", "Mi", "Joi", "Vi", "Sa", "Du"]
        first_dom_name = weekday_names[first_dom]
        planificator = self.this_month_ss.worksheet_by_title("Planificator")
        planificator.update_value("D116", first_dom_name)
        day_columns = [
            "D",
            "F",
            "H",
            "J",
            "L",
            "N",
            "P",
            "R",
            "T",
            "V",
            "X",
            "Z",
            "AB",
            "AD",
            "AF",
            "AH",
            "AJ",
            "AL",
            "AN",
            "AP",
            "AR",
            "AT",
            "AV",
            "AX",
            "AZ",
            "BB",
            "BD",
            "BF",
            "BH",
            "BJ",
            "BL",
        ]
        for d in range(1, month_days + 1):
            day = date(self.year, self.month, d)
            day_cell = f"{day_columns[d - 1]}117"
            if day in self.non_working_days:
                planificator.update_value(day_cell, "N")
            else:
                planificator.update_value(day_cell, "L")
        total_working_days = month_days - len(self.non_working_days)
        planificator.update_value("A13", month_days)
        planificator.update_value("A14", total_working_days)
        planificator.update_value("B14", f"{self.month_name} {self.year}")
        planificator.update_values(
            crange="D16:BM115", values=[["" for i in range(62)] for j in range(100)]
        )

        # * Insert nurses
        nurse_list = self.settings_ss.worksheet_by_title("Asistenti").range(
            "A3:B102", returnas="matrix"
        )
        planificator.update_values("A16:B115", nurse_list)

        # * Hide unused days when needed
        if month_days < 31:
            days_to_hide = 31 - month_days
            planificator.hide_dimensions(
                start=66 - (days_to_hide * 2), end=65, dimension="COLUMNS"
            )

            grafic = self.this_month_ss.worksheet_by_title("Grafic")
            grafic.hide_dimensions(start=34 - days_to_hide, end=34, dimension="COLUMNS")

            grafic_pe_zile = self.this_month_ss.worksheet_by_title("Grafic pe zile")
            grafic_pe_zile.hide_dimensions(
                start=71 - (days_to_hide * 2), end=70, dimension="ROWS"
            )

    def _insert_planner_link(self) -> None:
        grafice = self.settings_ss.worksheet_by_title("Grafice")
        target_row = (self.year - 2022) * 12 + self.month + 1
        grafice.cell(
            f"C{target_row}"
        ).formula = (
            f'HYPERLINK("{self.this_month_ss.url}", "{self.month_name} {self.year}")'
        )

    def _create_and_configure_new_ss(self) -> None:
        self._create_new_ss_from_model()
        self._configure_ss()
        self.this_month_ss.share("", role="writer", type="anyone")
        self._insert_planner_link()

    def get_or_create_new_ss(self) -> pygsheets.Spreadsheet.url:
        grafice = self.settings_ss.worksheet_by_title("Grafice")
        target_row = (self.year - 2022) * 12 + self.month + 1
        target_cell = f"C{target_row}"
        target_month_ss = grafice.cell(target_cell).formula
        if target_month_ss != "":
            target_month_ss_link = target_month_ss.split('"')[1].split("/")[5]
            if not self.this_month_ss:
                self.this_month_ss = self.client.open_by_key(target_month_ss_link)
        else:
            self._create_and_configure_new_ss()
        return self.this_month_ss.url

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def nurse_list(self) -> List[List[str | int]]:
        nurses_ws = self.settings_ss.worksheet_by_title("Asistenti")
        return nurses_ws.range("A3:AB101", returnas="matrix")

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def nurse_min_max(self) -> List[List[str | int]]:
        nurses_ws = self.settings_ss.worksheet_by_title("Asistenti")
        return nurses_ws.range("AD3:BE102", returnas="matrix")

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def sector_list(self) -> List[List[str | int]]:
        sectors_ws = self.settings_ss.worksheet_by_title("Sectoare")
        return sectors_ws.range("A3:F20", returnas="matrix")

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def position_list(self) -> List[List[str | int]]:
        sectors_ws = self.settings_ss.worksheet_by_title("Sectoare")
        return sectors_ws.range("N3:P22", returnas="matrix")

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def sectors_priority(self) -> List[List[str | int]]:
        sectors_ws = self.settings_ss.worksheet_by_title("Sectoare")
        return sectors_ws.range("N3:O22", returnas="matrix")

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def planned_rest_leaves(self) -> List[List[str | int]]:
        rl_ws = self.settings_ss.worksheet_by_title("CO")
        return rl_ws.get_values(
            "A3",
            "AW102",
            returnas="matrix",
            value_render=pygsheets.custom_types.ValueRenderOption.UNFORMATTED_VALUE,
        )

    @cached_property
    def month_details(self) -> Tuple[int, int, List[date]]:
        this_month_holidays = [d for d in self.holiday_list if d.month == self.month]
        return self.year, self.month, this_month_holidays

    @cached_property
    def month_days(self) -> int:
        return calendar.monthrange(self.year, self.month)[1]

    @cached_property
    @TimerLog(logger_name='scheduler.interface')
    def fixed_assignments(self) -> List[List[str | int]]:
        planificator = self.this_month_ss.worksheet_by_title("Planificator")
        return planificator.range("A16:BM115", returnas="matrix")

    @TimerLog(logger_name='scheduler.interface')
    def insert_shifts(self, solution_matrix: List[List[str]]) -> None:
        planificator = self.this_month_ss.worksheet_by_title("Planificator")
        planificator.update_values(crange="D16", values=solution_matrix)

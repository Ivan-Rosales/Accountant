import os
from calendar import month_name
from functools import cached_property
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook, Workbook

from app.core.settings import QSettings
from exceptions import ValidationException
from logger import logger


class BaseExecution:
    def __init__(self, *args, **kwargs):
        self.settings = QSettings()
        self.workdir = self.settings.get_workdir()


class FileExecution(BaseExecution):
    NUMBER_FORMAT = '_-* #,##0.00_-;\\-* #,##0.00_-;_-* "-"??_-;_-@_-'
    DATE_FORMAT = 'dd/mm/yyyy'

    @cached_property
    def filename(self) -> Path:
        raise NotImplementedError()

    @cached_property
    def workbook(self) -> Workbook:
        if self.filename.exists():
            try:
                workbook = load_workbook(self.filename)
            except BadZipFile:
                raise ValidationException(f'Hay un problema con el archivo\n{self.filename}')
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)

        return workbook

    @property
    def sheets(self):
        return getattr(self.workbook, '_sheets', [])

    @staticmethod
    def order_sheets(sheets: list):
        order_sheets = []
        months = [m.capitalize() for m in list(month_name)[1:]]

        for month in months:
            sheet = next((sheet for sheet in sheets if sheet.title == month), None)
            if sheet is None: continue
            order_sheets.append(sheet)

        for sheet in sheets:
            if sheet not in order_sheets:
                order_sheets.append(sheet)

        return order_sheets

    def get_sheet(self, sheet_name):
        return next((sheet for sheet in self.sheets if sheet.title == sheet_name), None)

    def save(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self.workbook._sheets = self.order_sheets(self.sheets)
        self.workbook.save(self.filename)

        logger.info(f'{self.__class__.__name__} saved in {self.filename}')

    def startfile(self):
        os.startfile(self.filename)

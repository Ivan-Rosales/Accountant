from calendar import month_name
from decimal import Decimal
from functools import cached_property
from pathlib import Path

from openpyxl.styles import Border, Side

from base.execution import WorkbookExecution
from exceptions import ValidationException
from execution.month_summary import MonthSummary
from logger import logger
from models import Cliente


class YearSummary(WorkbookExecution):
    def __init__(self, client: Cliente, year: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.year = year

        self._file = None

        self.validate()

    @cached_property
    def filename(self):
        if self._file is not None: return self._file
        filename = f'{self.client.rfc} {self.year}'.upper()
        return Path(f'{self.workdir}/{self.client.rfc}/{filename}.xlsx')

    def validate(self):
        if not isinstance(self.client, Cliente):
            raise ValidationException('No se ha asignado un cliente')

    def generate_sheet(self, month, force_new=False, prev=None):
        name = month_name[month].capitalize()
        logger.info(f'{self.__class__.__name__} generating sheet {name} {month}')

        sheet = self.get_sheet(name)
        has_sheet = sheet is not None

        if sheet is None or force_new:
            sheet = self.workbook.create_sheet(name)
            sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE

            if not has_sheet and 2 < month and month % 2 == 0:
                self.generate_sheet_payment(month)

        self.set_labels(sheet, month)
        self.set_data(sheet, month, prev)
        self.set_format(sheet)

        logger.info(f'{self.__class__.__name__} generated sheet {name} {month}')
        return sheet

    def generate_sheet_payment(self, month):
        name = month_name[month].capitalize()
        prev_name = month_name[month - 1].capitalize()

        prev_sheet = self.get_sheet(prev_name)
        if prev_sheet is None:
            prev_sheet = self.generate_sheet(month - 1)

        total_ingresos = Decimal(prev_sheet.cell(row=6, column=2).value)
        total_egresos = Decimal(prev_sheet.cell(row=7, column=2).value)
        total_iva = Decimal(prev_sheet.cell(row=24, column=2).value)

        sheet = self.generate_sheet(month, force_new=True, prev=(total_ingresos, total_egresos, total_iva))
        sheet.title = f'{name} pago'

        sheet.cell(row=11, column=1).value = f'total de ingresos de {prev_name}'.upper()
        sheet.cell(row=18, column=1).value = f'total de egresos de {prev_name}'.upper()
        sheet.cell(row=26, column=4).value = 'pago'.upper()

    def set_labels(self, sheet, month):
        def get_totals_label(label) -> str:
            if month == 1: return ''
            if month == 2: return f'total de {label} de {month_name[month - 1]}'
            return f'total de ingresos de {label} de enero a {month_name[month - 1]}'

        name = month_name[month].capitalize()

        # Headers
        sheet.cell(row=1, column=1).value = str(self.client.fullname()).upper()
        sheet.cell(row=2, column=1).value = 'concentrado de mes'.upper()
        sheet.cell(row=3, column=1).value = f'{name} {self.year}'.upper()

        # Titles
        sheet.cell(row=6, column=1).value = f'ingresos'.upper()
        sheet.cell(row=7, column=1).value = f'egresos'.upper()
        sheet.cell(row=6, column=4).value = f'iva causado'.upper()
        sheet.cell(row=7, column=4).value = f'iva acreditable'.upper()

        # Totals
        sheet.cell(row=10, column=1).value = f'total de ingresos de {name}'.upper()
        sheet.cell(row=11, column=1).value = get_totals_label('ingresos').upper()
        sheet.cell(row=12, column=1).value = 'total'.upper()

        sheet.merge_cells(start_row=10, start_column=1, end_row=10, end_column=4)
        sheet.merge_cells(start_row=11, start_column=1, end_row=11, end_column=4)
        sheet.merge_cells(start_row=12, start_column=1, end_row=12, end_column=4)

        sheet.cell(row=17, column=1).value = f'total de egresos de {name}'.upper()
        sheet.cell(row=18, column=1).value = get_totals_label('egresos').upper()
        sheet.cell(row=19, column=1).value = 'total'.upper()

        sheet.merge_cells(start_row=17, start_column=1, end_row=17, end_column=4)
        sheet.merge_cells(start_row=18, start_column=1, end_row=18, end_column=4)
        sheet.merge_cells(start_row=19, start_column=1, end_row=19, end_column=4)

        # Iva
        sheet.cell(row=22, column=1).value = 'iva causado'.upper()
        sheet.cell(row=23, column=1).value = 'iva acreditable'.upper()
        sheet.cell(row=24, column=1).value = 'iva de diferencia'.upper()
        sheet.cell(row=25, column=1).value = 'iva saldo anterior'.upper()
        sheet.cell(row=26, column=1).value = 'iva a cargo o favor'.upper()

    def get_prev_data(self, month):
        month = month - 1
        if month == 0: return Decimal(0), Decimal(0), Decimal(0)
        name = month_name[month].capitalize()
        sheet = self.get_sheet(name)
        if sheet is None: sheet = self.generate_sheet(month)

        total_ingresos = Decimal(sheet.cell(row=12, column=5).value)
        total_egresos = Decimal(sheet.cell(row=19, column=5).value)
        total_iva = Decimal(sheet.cell(row=26, column=2).value)

        logger.debug(f'{self.__class__.__name__} got data from {name} ({total_ingresos}, {total_egresos}, {total_iva})')

        return total_ingresos, total_egresos, total_iva

    def get_month_file(self, month, kind=''):
        rev = kind == 'ingresos'
        return MonthSummary(self.client, year=self.year, month=month, rev=rev)

    def set_data(self, sheet, month, previous=None):
        if isinstance(previous, (list, tuple)) and len(previous) == 3:
            prev_ingresos, prev_egresos, prev_iva = previous
        else:
            prev_ingresos, prev_egresos, prev_iva = self.get_prev_data(month)

        # Ingresos
        ingresos_file = self.get_month_file(month, 'ingresos')
        sheet.cell(row=6, column=2).value = ingresos_file.subtotal
        sheet.cell(row=6, column=5).value = ingresos_file.iva

        ingresos_total = ingresos_file.subtotal + prev_ingresos
        sheet.cell(row=10, column=5).value = ingresos_file.subtotal
        sheet.cell(row=11, column=5).value = prev_ingresos
        sheet.cell(row=12, column=5).value = ingresos_total
        sheet.cell(row=12, column=6).value = ingresos_total

        if 0 < ingresos_file.ieps:
            sheet.cell(row=14, column=1).value = 'ieps ingresos'.upper()
            sheet.cell(row=14, column=2).value = ingresos_file.ieps

        # Egresos
        egresos_file = self.get_month_file(month, 'egresos')
        sheet.cell(row=7, column=2).value = egresos_file.subtotal
        sheet.cell(row=7, column=5).value = egresos_file.iva

        egresos_total = egresos_file.subtotal + prev_egresos
        sheet.cell(row=17, column=5).value = egresos_file.subtotal
        sheet.cell(row=18, column=5).value = prev_egresos
        sheet.cell(row=19, column=5).value = egresos_total
        sheet.cell(row=19, column=6).value = egresos_total

        if 0 < egresos_file.ieps:
            sheet.cell(row=15, column=1).value = 'ieps egresos'.upper()
            sheet.cell(row=15, column=2).value = egresos_file.ieps

        # Totals
        sheet.cell(row=20, column=6).value = ingresos_total - egresos_total

        iva_diff = abs(ingresos_file.iva - egresos_file.iva)
        sheet.cell(row=22, column=2).value = ingresos_file.iva
        sheet.cell(row=23, column=2).value = egresos_file.iva
        sheet.cell(row=24, column=2).value = iva_diff
        sheet.cell(row=25, column=2).value = prev_iva
        sheet.cell(row=26, column=2).value = abs(iva_diff - prev_iva)

    def set_format(self, sheet):
        for row in range(1, sheet.max_row + 1):
            for column in range(1, sheet.max_column + 1):
                cell = sheet.cell(row=row, column=column)
                if isinstance(cell.value, (Decimal, float, int)):
                    cell.number_format = self.NUMBER_FORMAT

        # border bottom
        border = Border(bottom=Side(style='thin'))
        sheet.cell(row=11, column=5).border = border
        sheet.cell(row=18, column=5).border = border
        sheet.cell(row=19, column=6).border = border
        sheet.cell(row=23, column=2).border = border
        sheet.cell(row=25, column=2).border = border

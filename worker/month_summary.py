import os
from calendar import month_name
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_DOWN
from functools import cached_property
from pathlib import Path
from typing import Dict

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment

from app.core.settings import QSettings
from exceptions import ValidationException
from functions import normalize_number
from logger import logger
from models import Cliente
from settings import DEFAULT_WORK_DIR
from worker.xml_file import XmlFile

NUMBER_FORMAT = '_-* #,##0.00_-;\\-* #,##0.00_-;_-* "-"??_-;_-@_-'
DATE_FORMAT = 'dd/mm/yyyy'


class MonthSummary:
    columns_row = 4
    column_data = 4

    def __init__(self, client: Cliente):
        self.client = client

        self._workbook = None
        self._sheet = None

        self.xml_files: Dict[str:XmlFile] = {}

        self.has_ieps = False
        self.has_ret_isr = False
        self.has_ret_iva = False
        self.header_set = False
        self.columns_set = False
        self.footer_set = False
        self.rev = False

        self.year = None
        self.month = None

        self.validate()

        settings = QSettings()
        self.workdir = settings.value('test', DEFAULT_WORK_DIR)

    @cached_property
    def filename(self):
        kind = 'ingresos' if self.rev else 'egresos'
        filename = f'{self.client.rfc} {self.year} {kind}'.upper()
        return Path(f'{self.workdir}/{filename}.xlsx')

    @cached_property
    def workbook(self):
        if self.filename.exists():
            workbook = load_workbook(self.filename)
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)

        return workbook

    @cached_property
    def sheet(self):
        sheet_name = month_name[self.month].capitalize()
        return self.workbook.create_sheet(sheet_name)

    def validate(self):
        if self.client is None:
            raise ValidationException('No se ha asignado un cliente')

    def validate_file(self, xml: XmlFile):
        emisor_rfc = xml.emisor.rfc
        receptor_rfc = xml.receptor.rfc

        if self.client.rfc not in [emisor_rfc, receptor_rfc]:
            raise ValidationException(
                f'El cliente seleccionado ({self.client.rfc.upper()}) no corresponde con los clientes del xml '
                f'[{emisor_rfc.upper()}, {receptor_rfc.upper()}]'
            )

    def add_files_in_folder(self, path: Path):
        iterdir = path.iterdir()
        files = [i for i in iterdir if i.is_file()]
        xml_paths = [i for i in files if i.suffix == '.xml']
        xml_files = [XmlFile(i) for i in xml_paths]
        xml_files.sort(key=lambda x: x.date)

        self.xml_files = {i.uuid: i for i in xml_files}

        for xml_file in self.xml_files.values():
            self.validate_file(xml_file)
            self.add_file(xml_file)

    def set_header(self, xml: XmlFile):
        self.year = xml.date.year
        self.month = xml.date.month
        self.rev = self.client.rfc == xml.emisor.rfc

        self.sheet.cell(row=1, column=1).value = str(self.client).upper()
        self.sheet.cell(row=2, column=1).value = f'concentrado de {'ingresos' if self.rev else 'egresos'}'.upper()
        self.sheet.cell(row=3, column=1).value = xml.date.strftime('%B %Y').upper()

        self.sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
        self.sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        self.sheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=3)

        self.header_set = True

    def set_columns(self):
        self.has_ieps = any(i.ieps > 0 for i in self.xml_files.values())
        self.has_ret_isr = any(i.ret_isr > 0 for i in self.xml_files.values())
        self.has_ret_iva = any(i.ret_iva > 0 for i in self.xml_files.values())

        columns = ['subtotal', 'iva', 'total']

        if self.has_ieps:
            columns = ['no gravado', 'gravado', 'ieps', 'iva', 'total']

        if self.has_ret_isr or self.has_ret_iva:
            columns += ['ret iva', 'ret isr', 'neto']

        for column, label in enumerate(columns, self.column_data):
            self.sheet.cell(row=self.columns_row, column=column).value = label.upper()

        self.columns_set = True

    def add_file(self, xml: XmlFile):
        if not self.header_set: self.set_header(xml)
        if not self.columns_set: self.set_columns()

        if xml.uuid not in self.xml_files:
            self.xml_files[xml.uuid] = xml

        kind = self.rev
        row = max([6, self.sheet.max_row + 1])

        self.sheet.cell(row=row, column=1).value = xml.date
        self.sheet.cell(row=row, column=2).value = (xml.receptor.name if kind else xml.emisor.name).upper()
        self.sheet.cell(row=row, column=3).value = f'F/{xml.uuid.split('-')[-1]}'.upper()

        gravado = normalize_number(xml.iva * Decimal(6.25) if self.has_ieps else 0, rounding=ROUND_HALF_DOWN)
        subtotal = xml.total - xml.ieps - xml.iva - gravado
        total = xml.total
        ieps = xml.ieps
        iva = xml.iva

        # delete insignificant values
        if self.has_ieps and 1.16 < total:
            if abs(subtotal) < 1 or subtotal < 0:
                gravado += subtotal
                subtotal = Decimal(0)

        # type P invoices have no effect
        if xml.tipo == 'P':
            subtotal = gravado = ieps = iva = total = Decimal(0)

        # type E invoices have reverse effect
        if xml.tipo == 'E':
            subtotal = subtotal * Decimal(-1)
            gravado = gravado * Decimal(-1)
            total = total * Decimal(-1)
            ieps = ieps * Decimal(-1)
            iva = iva * Decimal(-1)

        column = 4
        self.sheet.cell(row=row, column=column).value = subtotal

        if self.has_ieps:
            self.sheet.cell(row=row, column=column + 1).value = gravado
            self.sheet.cell(row=row, column=column + 2).value = ieps
            column += 2

        self.sheet.cell(row=row, column=column + 1).value = iva
        self.sheet.cell(row=row, column=column + 2).value = total

    def set_format(self):
        for row in range(6, self.sheet.max_row + 1):
            self.sheet.cell(row=row, column=1).number_format = DATE_FORMAT

        for column in range(self.column_data, self.sheet.max_column + 1):
            self.sheet.cell(row=self.columns_row, column=column).alignment = Alignment(horizontal="center")

        for row in range(self.columns_row + 2, self.sheet.max_row + 1):
            for column in range(self.column_data, self.sheet.max_column + 1):
                self.sheet.cell(row=row, column=column).number_format = NUMBER_FORMAT

    def set_footer(self):
        min_col = self.column_data
        max_row = self.sheet.max_row
        min_row = self.columns_row + 2
        max_col = self.sheet.max_column

        summaries = defaultdict(Decimal)
        for row in self.sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                summaries[cell.column] += cell.value

        max_row += 2
        for column, total in summaries.items():
            self.sheet.cell(row=max_row, column=column).value = total

    def transform_sheets(self, sheets: list):
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

    def save(self):
        if len(self.xml_files.keys()) == 0:
            raise ValidationException('El concentrado no tiene archivos')

        if not self.footer_set: self.set_footer()
        self.set_format()

        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self.workbook._sheets = self.transform_sheets(self.workbook._sheets)
        self.workbook.save(self.filename)

        logger.info(f'save month summary in {self.filename}')

    def startfile(self):
        os.startfile(self.filename)

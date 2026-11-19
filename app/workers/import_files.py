from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from openpyxl import load_workbook

from execution.month_summary import MonthSummary
from execution.year_summary import YearSummary
from functions import normalize_number


@dataclass
class MonthSummaryFake:
    subtotal: Decimal
    ieps: Decimal
    iva: Decimal


@dataclass
class PersonFake:
    rfc: str
    name: str


@dataclass
class XmlFileFake:
    tipo: str
    uuid: str
    date: datetime
    emisor: PersonFake
    receptor: PersonFake
    ret_isr: Decimal
    ret_iva: Decimal
    total: Decimal
    ieps: Decimal
    iva: Decimal


class ImportFilesWorker(QObject):
    start = Signal(Path, dict)
    success = Signal(object)
    progress = Signal(float, int, object)
    error = Signal(object)

    files = []
    client = None
    clients = None
    workbook = None
    year = None

    def search_files(self, path):
        for i in path.iterdir():
            if i.is_dir():
                self.search_files(i)

            if i.is_file() and i.suffix.lower() == '.xlsx':
                self.files.append(i)

    def generate_new_files(self):
        n_files = len(self.files)
        self.progress.emit(0, n_files, None)

        summary = {}

        for c, file in enumerate(self.files, 1):
            try:
                year, rfc, tipo = file.name.split(' ', 2)
                cliente = self.clients.get(rfc)
                if not year.isdigit(): continue
                if cliente is None: continue

                self.client = cliente
                self.year = int(year)
                is_year = 'concentradomes' in tipo.lower()

                if is_year:
                    self.generate_year_file(file)
                else:
                    self.generate_month_file(file)

                self.progress.emit(c / n_files, n_files, file)
                summary[file] = True, None
            except Exception as error:
                summary[file] = False, error

        return summary

    def get_prev_data(self, month):
        month = month - 1
        if month == 0: return Decimal(0), Decimal(0), Decimal(0)

        sheets = getattr(self.workbook, '_sheets', [])
        sheet = next((sheet for sheet in sheets if sheet.title == str(month)), None)
        if sheet is None: return Decimal(0), Decimal(0), Decimal(0)

        ingresos = normalize_number(sheet.cell(row=11, column=5).value)
        prev_ingresos = normalize_number(sheet.cell(row=6, column=2).value)

        egresos = normalize_number(sheet.cell(row=18, column=5).value)
        prev_egresos = normalize_number(sheet.cell(row=7, column=2).value)

        iva_causado = normalize_number(sheet.cell(row=6, column=5).value)
        iva_acreditado = normalize_number(sheet.cell(row=7, column=5).value)
        prev_iva = normalize_number(sheet.cell(row=25, column=2).value)

        return (
            normalize_number(ingresos + prev_ingresos),
            normalize_number(egresos + prev_egresos),
            (abs(abs(iva_causado - iva_acreditado) + prev_iva)),
        )

    def get_month_file(self, month, kind=''):
        sheets = getattr(self.workbook, '_sheets', [])
        sheet = next((sheet for sheet in sheets if sheet.title == str(month)), None)
        if sheet is None: return MonthSummaryFake(subtotal=Decimal(0), iva=Decimal(0), ieps=Decimal(0))

        if kind == 'ingresos':
            iva_value = normalize_number(sheet.cell(row=6, column=5).value)
            subtotal_value = normalize_number(sheet.cell(row=6, column=2).value)
            ieps_value = normalize_number(sheet.cell(row=14, column=2).value or '0')
        else:
            iva_value = normalize_number(sheet.cell(row=7, column=5).value)
            subtotal_value = normalize_number(sheet.cell(row=7, column=2).value)
            ieps_value = normalize_number(sheet.cell(row=15, column=2).value or '0')

        return MonthSummaryFake(subtotal=subtotal_value, iva=iva_value, ieps=ieps_value)

    def generate_year_file(self, file):
        year = int(file.name.split(' ')[0])
        summary = YearSummary(self.client, year)
        summary.get_prev_data = self.get_prev_data
        summary.get_month_file = self.get_month_file

        self.workbook = load_workbook(file.absolute())
        sheets = getattr(self.workbook, '_sheets', [])
        generate_to = max([int(sheet.title) if sheet.title.isdigit() else 0 for sheet in sheets])
        summary.generate_sheet(generate_to)
        summary.save()

    def get_columns(self, sheet, row, fields, columns_row=4):
        title_row = sheet[columns_row]
        columns = [i.column for i in title_row if isinstance(i.value, str) and i.value.lower() in fields]
        values = [sheet.cell(row=row, column=column).value for column in columns]
        return normalize_number(Decimal(sum([normalize_number(Decimal(value)) for value in values])))

    def generate_month_file(self, file):
        summary = MonthSummary(self.client)

        workbook = load_workbook(file.absolute())

        sheet = workbook.active

        kind = 'ingresos' in (sheet.cell(row=2, column=1).value or '').lower()

        max_row = sheet.max_row
        for row in sheet.iter_rows(min_row=6, max_row=max_row, min_col=1, max_col=3):
            date_cell = row[0]
            name_cell = row[1]
            uuid_cell = row[2]

            if not isinstance(date_cell.value, datetime):
                continue

            iva = self.get_columns(sheet, date_cell.row, ['iva'])
            ieps = self.get_columns(sheet, date_cell.row, ['ieps'])
            total = self.get_columns(sheet, date_cell.row, ['total'])
            ret_iva = self.get_columns(sheet, date_cell.row, ['ret iva'])
            ret_isr = self.get_columns(sheet, date_cell.row, ['ret isr'])

            if kind:
                receptor = PersonFake(rfc='', name=name_cell.value)
                emisor = PersonFake(rfc=self.client.rfc, name=self.client.fullname())
            else:
                emisor = PersonFake(rfc='', name=name_cell.value)
                receptor = PersonFake(rfc=self.client.rfc, name=self.client.fullname())

            xml = XmlFileFake(date=date_cell.value, emisor=emisor, total=total, ieps=ieps, iva=iva, ret_isr=ret_isr,
                              uuid=f'{datetime.now().timestamp()}-{uuid_cell.value[2:]}', tipo='', receptor=receptor,
                              ret_iva=ret_iva)

            summary.xml_files[xml.uuid] = xml

        summary.process_files()
        summary.save()

    def on_start(self, path, clients):
        try:
            self.files = []  # por instancia y por corrida: antes era una lista de clase que se acumulaba
            self.clients = clients
            self.search_files(path)
            summary = self.generate_new_files()
            self.success.emit(summary)
        except Exception as error:
            self.error.emit(error)

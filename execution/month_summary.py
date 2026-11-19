from calendar import month_name
from collections import defaultdict
from decimal import Decimal
from functools import cached_property
from pathlib import Path
from typing import Dict

from openpyxl.styles import Alignment

from base.execution import WorkbookExecution
from exceptions import ValidationException
from execution.xml_file import XmlFile

GENERIC_RFCS = {'XAXX010101000', 'XEXX010101000'}
PUBLICO_EN_GENERAL = 'PUBLICO EN GENERAL'
from functions import normalize_number, decimal_property
from logger import logger
from models import Cliente


class MonthSummary(WorkbookExecution):
    columns_row = 4
    column_data = 4

    def __init__(self, client: Cliente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self._file = None

        self._workbook = None
        self._sheet = None

        self.xml_files: Dict[str:XmlFile] = {}

        self.header_set = False
        self.columns_set = False
        self.footer_set = False
        self.rev = kwargs.get('rev', False)

        self.year = kwargs.get('year')
        self.month = kwargs.get('month')

        self.validate()

    def __str__(self):
        kind = ('ingresos' if self.rev else 'egresos').capitalize()
        return f'<MonthSummary kind: {kind}, client: {self.client}, year: {self.year}, month: {self.month}/>'

    @cached_property
    def filename(self):
        if self._file is not None: return self._file
        kind = 'ingresos' if self.rev else 'egresos'
        filename = f'{self.client.rfc} {self.year} {kind}'.upper()
        return Path(f'{self.workdir}/{self.client.rfc}/{filename}.xlsx')

    @cached_property
    def sheet(self):
        sheet_name = month_name[self.month].capitalize()
        sheet = self.get_sheet(sheet_name)
        replace_sheet = sheet is not None

        if replace_sheet:
            self.workbook.remove(sheet)

        sheet = self.workbook.create_sheet(sheet_name)
        logger.info(f'{self.__class__.__name__} {'replacing' if replace_sheet else 'generating'} {sheet_name}')

        sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE
        return sheet

    @cached_property
    def has_ieps(self):
        return any(i.ieps > 0 for i in self.xml_files.values())

    @cached_property
    def has_ret_isr(self):
        return any(i.ret_isr > 0 for i in self.xml_files.values())

    @cached_property
    def has_ret_iva(self):
        return any(i.ret_iva > 0 for i in self.xml_files.values())

    @cached_property
    def has_ret(self):
        return self.has_ret_isr or self.has_ret_iva

    def validate(self):
        if not isinstance(self.client, Cliente):
            raise ValidationException('No se ha asignado un cliente')

    def validate_file(self, xml: XmlFile):
        emisor_rfc = xml.emisor.rfc
        receptor_rfc = xml.receptor.rfc

        if self.client.rfc not in [emisor_rfc, receptor_rfc]:
            raise ValidationException(
                f'El cliente seleccionado ({self.client.rfc.upper()}) no corresponde con los clientes del xml '
                f'[{emisor_rfc.upper()}, {receptor_rfc.upper()}]'
            )

    @staticmethod
    def load_folder(path: Path) -> list[XmlFile]:
        """Lee todos los .xml de la carpeta (y subcarpetas), sin duplicados por UUID, ordenados por fecha."""
        xml_paths = sorted(i for i in path.rglob('*') if i.is_file() and i.suffix.lower() == '.xml')
        unique = {xml.uuid: xml for xml in (XmlFile(i) for i in xml_paths)}
        return sorted(unique.values(), key=lambda x: x.date)

    def add_files_in_folder(self, path: Path):
        self.add_records(self.load_folder(path))

    def add_records(self, records):
        """Genera la hoja con CFDI leídos de XML o guardados en la base de datos (misma interfaz)."""
        records = sorted(records, key=lambda x: (x.date, x.uuid))
        self.xml_files = {i.uuid: i for i in records}
        self.validate_batch(records)
        self.process_files()

    def validate_batch(self, xml_files):
        """Un concentrado es de un solo mes y un solo tipo (ingresos o egresos)."""
        for xml in xml_files:
            self.validate_file(xml)

        relevant = [i for i in xml_files if i.tipo != 'N']
        months = sorted({(i.date.year, i.date.month) for i in relevant})
        if len(months) > 1:
            labels = ', '.join(f'{month_name[m].capitalize()} {y}' for y, m in months)
            raise ValidationException(f'Los archivos son de varios meses ({labels}).\n'
                                      f'Genere un ZIP por mes.')

        kinds = {self.client.rfc == i.emisor.rfc for i in relevant}
        if len(kinds) > 1:
            raise ValidationException('Los archivos mezclan facturas emitidas (ingresos) y recibidas (egresos).\n'
                                      'Genere un ZIP para cada tipo.')

    def process_files(self):
        for xml_file in self.xml_files.values():
            self.validate_file(xml_file)
            self.add_file(xml_file)

    def set_header(self, xml: XmlFile):
        self.year = xml.date.year
        self.month = xml.date.month
        self.rev = self.client.rfc == xml.emisor.rfc

        self.sheet.cell(row=1, column=1).value = str(self.client.fullname()).upper()
        self.sheet.cell(row=2, column=1).value = f'concentrado de {'ingresos' if self.rev else 'egresos'}'.upper()
        self.sheet.cell(row=3, column=1).value = xml.date.strftime('%B %Y').upper()

        self.sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
        self.sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        self.sheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=3)

        self.header_set = True

    @property
    def column_labels(self):
        columns = ['subtotal', 'iva', 'total']

        if self.has_ieps:
            columns = ['no gravado', 'gravado', 'ieps', 'iva', 'total']

        if self.has_ret:
            columns += ['ret iva', 'ret isr', 'neto']

        return columns

    def row_values(self, xml) -> dict:
        """Importes del renglón en pesos. Notas de crédito (E) en negativo; pagos (P) en cero.

        - TOTAL es el importe antes de retenciones y NETO lo efectivamente cobrado/pagado.
        - SUBTOTAL = TOTAL - IVA - IEPS: incluye impuestos locales y cualquier diferencia de
          redondeo del CFDI, para que el renglón siempre cuadre con el total.
        - GRAVADO es el valor de actos a tasa de IVA > 0, leído de los conceptos (no IVA x 6.25).
        """
        zero = Decimal(0)
        if xml.tipo == 'P':
            return {k: zero for k in ('subtotal', 'no gravado', 'gravado', 'ieps', 'iva', 'total',
                                      'ret iva', 'ret isr', 'neto')}

        sign = Decimal(-1) if xml.tipo == 'E' else Decimal(1)
        neto = xml.total * sign
        ret_iva = xml.ret_iva * sign
        ret_isr = xml.ret_isr * sign
        iva = xml.iva * sign
        ieps = xml.ieps * sign
        total = neto + ret_iva + ret_isr
        subtotal = total - iva - ieps

        gravado = getattr(xml, 'gravado', None)
        gravado = subtotal if gravado is None else min(gravado * sign, subtotal, key=abs)

        return {
            'subtotal': subtotal,
            'gravado': gravado,
            'no gravado': subtotal - gravado,
            'ieps': ieps,
            'iva': iva,
            'total': total if self.has_ret else neto,
            'ret iva': ret_iva,
            'ret isr': ret_isr,
            'neto': neto,
        }

    def set_columns(self):
        columns = self.column_labels

        for column, label in enumerate(columns, self.column_data):
            self.sheet.cell(row=self.columns_row, column=column).value = label.upper()

        self.columns_set = True

    def add_file(self, xml: XmlFile, row=None):
        if not self.header_set: self.set_header(xml)
        if not self.columns_set: self.set_columns()

        if xml.uuid not in self.xml_files:
            self.xml_files[xml.uuid] = xml

        if xml.tipo == 'N': return

        row = row or max([6, self.sheet.max_row + 1])
        values = self.row_values(xml)

        counterpart = xml.receptor if self.rev else xml.emisor
        name = PUBLICO_EN_GENERAL if counterpart.rfc in GENERIC_RFCS else (counterpart.name or counterpart.rfc)

        self.sheet.cell(row=row, column=1).value = xml.date
        self.sheet.cell(row=row, column=2).value = (name or '').upper()
        self.sheet.cell(row=row, column=3).value = f'F/{xml.uuid.split('-')[-1]}'.upper()

        for column, label in enumerate(self.column_labels, self.column_data):
            self.sheet.cell(row=row, column=column).value = values[label]

        logger.info(f'{self.__class__.__name__} added file {xml.uuid}')

    def set_format(self):
        for row in range(6, self.sheet.max_row + 1):
            self.sheet.cell(row=row, column=1).number_format = self.DATE_FORMAT

        for column in range(self.column_data, self.sheet.max_column + 1):
            self.sheet.cell(row=self.columns_row, column=column).alignment = Alignment(horizontal="center")

        for row in range(self.columns_row + 2, self.sheet.max_row + 1):
            for column in range(self.column_data, self.sheet.max_column + 1):
                self.sheet.cell(row=row, column=column).number_format = self.NUMBER_FORMAT

    def set_footer(self, total_offset=0):
        min_col = self.column_data
        max_row = self.sheet.max_row
        min_row = self.columns_row + 2
        max_col = self.sheet.max_column

        summaries = defaultdict(Decimal)
        for row in self.sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                if not isinstance(cell.value, Decimal): continue
                summaries[cell.column] += cell.value

        max_row += 2 + total_offset
        for column, total in summaries.items():
            self.sheet.cell(row=max_row, column=column).value = total

    def get_column_totals(self, fields):
        sheet_name = month_name[self.month].capitalize()
        sheet = self.get_sheet(sheet_name)
        if sheet is None: return Decimal(0)

        title_row = sheet[self.columns_row]
        cols = [i.column for i in title_row if isinstance(i.value, str) and i.value.lower() in fields]
        values = [Decimal(sheet.cell(row=sheet.max_row, column=column).value or 0) for column in cols]
        return sum(values)

    @cached_property
    @decimal_property
    def iva(self):
        return self.get_column_totals(['iva'])

    @cached_property
    @decimal_property
    def ieps(self):
        return self.get_column_totals(['ieps'])

    @cached_property
    @decimal_property
    def subtotal(self):
        return self.get_column_totals(['subtotal', 'no gravado', 'gravado'])

    def from_file(self, filepath):
        self._file = filepath

    def save(self):
        if len(self.xml_files.keys()) == 0:
            raise ValidationException('El concentrado no tiene archivos')

        if not self.footer_set: self.set_footer()
        self.set_format()

        super().save()


class RowProviders:
    def __init__(self, client, xml_files):
        self.client = client
        self.xml_files = xml_files
        self.row = [''] * 7 + ['0'] * 47
        self.set_data()

    def get_total(self):
        return sum([i.total for i in self.xml_files])

    def get_total_iva(self):
        return sum([i.iva for i in self.xml_files])

    def set_data(self):
        self.row[0] = '04'
        self.row[1] = '85'
        self.row[2] = self.client.rfc
        self.row[11] = self.get_total()
        self.row[21] = self.get_total_iva()
        self.row[53] = '01'

    def csv_row(self):
        return self.row

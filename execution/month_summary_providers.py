import csv
from collections import defaultdict
from decimal import Decimal
from functools import cached_property
from pathlib import Path

from openpyxl.styles import Border, Side
from openpyxl.styles import PatternFill

from execution.month_summary import MonthSummary
from execution.month_summary import RowProviders
from execution.xml_file import XmlFile, XmlNode
from logger import logger


class MonthSummaryProviders(MonthSummary):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.providers = defaultdict(list)

    @cached_property
    def filename(self):
        if self._file is not None: return self._file
        kind = 'ingresos' if self.rev else 'egresos'
        filename = f'{self.client.rfc} {self.year} {kind} proveedores'.upper()
        return Path(f'{self.workdir}/{self.client.rfc}/{filename}.xlsx')

    def set_header(self, xml: XmlFile):
        super().set_header(xml)
        self.sheet.cell(row=2, column=1).value += ' proveedores'.upper()

    def add_file(self, xml: XmlFile):
        if not self.header_set: self.set_header(xml)
        if not self.columns_set: self.set_columns()

        if xml.uuid not in self.xml_files:
            self.xml_files[xml.uuid] = xml

        rfc_related = (xml.receptor.rfc if self.rev else xml.emisor.rfc).upper()
        self.providers[rfc_related].append(xml)

        logger.info(f'{self.__class__.__name__} added file {xml.uuid}')

    def set_footer(self, total_offset=-1):
        first = True
        for rfc, xmls in self.providers.items():
            row = max([6, self.sheet.max_row + 1]) + (0 if first else 1)
            first = False

            for i, xml in enumerate(xmls):
                super().add_file(xml, row + i)

            super().set_footer(total_offset)
            self.columns_row = self.columns_row + len(xmls) + 2

    def set_format(self):
        self.columns_row = 4
        super().set_format()

        border = Border(top=Side(style='thin'))
        for row in range(self.columns_row + 2, self.sheet.max_row + 1):
            for column in range(self.column_data, self.sheet.max_column + 1):
                cell = self.sheet.cell(row=row, column=column)
                cell_below = self.sheet.cell(row=row + 1, column=column)
                if isinstance(cell_below.value, Decimal): continue
                cell.border = border

    def save(self):
        self.generate_providers()
        return super().save()

    def generate_providers(self):
        providers = defaultdict(list)
        for xml_file in self.xml_files.values():
            if xml_file.tipo == 'N': continue  # los trabajadores no son proveedores (DIOT)
            person: XmlNode = xml_file.receptor if self.rev else xml_file.emisor
            providers[person].append(xml_file)

        kind = 'ingresos' if self.rev else 'egresos'
        filename = f'{self.client.rfc} {self.year} {self.month} {kind}'.upper()
        filename = Path(f'{self.workdir}/{self.client.rfc}/proveedores/{filename}.txt')
        filename.parent.mkdir(parents=True, exist_ok=True)
        file = open(filename, 'w', newline='')

        try:
            writer = csv.writer(file, delimiter='|')
            for person, xml_files in providers.items():
                row = RowProviders(person, xml_files)
                writer.writerow(row.csv_row())
        finally:
            file.close()

        logger.info(f'{self.__class__.__name__} providers saved in {self.filename}')

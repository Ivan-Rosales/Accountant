import os
from pathlib import Path

from PySide6.QtWidgets import QMessageBox
from openpyxl import Workbook

from app.logs.logger import logger
from app.models.client import Client
from core.xml_file import XmlFile


class MonthSummary:
    def __init__(self, client: Client):
        self.workbook = Workbook()
        self.sheet = self.workbook.active
        self.client = client

        self.header_set = False
        self._columns = None
        self.rev = None

        self.validate()

    def validate(self):
        if self.client is None:
            raise Exception('no client selected')

    def validate_file(self, xml: XmlFile):
        emisor_rfc = xml.emisor.rfc
        receptor_rfc = xml.receptor.rfc

        if self.client.rfc not in [emisor_rfc, receptor_rfc]:
            raise Exception(
                f'selected client ({self.client.rfc}) dont correspond with the xml file '
                f'[{emisor_rfc}, {receptor_rfc}]'
            )

    def add_files_in_folder(self, path: Path):
        iterdir = path.iterdir()
        files = [i for i in iterdir if i.is_file()]
        xml_paths = [i for i in files if i.suffix == '.xml']
        xml_files = [XmlFile(i) for i in xml_paths]

        for xml_file in xml_files:
            self.validate_file(xml_file)
            self.add_file(xml_file)

    def set_header(self, xml: XmlFile):
        kind = self.rev = self.client.rfc == xml.emisor.rfc

        self.sheet.cell(row=1, column=1).value = self.client.fullname().upper()
        self.sheet.cell(row=2, column=1).value = f'concentrado de {'EGRESOS' if kind else 'INGRESOS'}'.upper()
        self.sheet.cell(row=3, column=1).value = xml.date.strftime('%B %Y').upper()

        print(xml.ieps)
        print(xml.ieps)
        print(xml.ieps)

        self.header_set = True

    def add_file(self, xml: XmlFile):
        if not self.header_set: self.set_header(xml)

    def save(self):
        path = Path('month_summary.xlsx').absolute()
        self.workbook.save(path)

        logger.info(f'save month summary in {path}')

        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        text = f'Se generó correctamente.\n{path}'
        response = QMessageBox.question(None, 'about', text, buttons)
        open_file = response == QMessageBox.StandardButton.Yes
        if open_file: os.startfile(path)

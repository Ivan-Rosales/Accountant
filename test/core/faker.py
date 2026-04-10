from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import ElementTree, parse

from execution.xml_file import XmlFile


class XmlFileFaker:
    def __init__(self, client):
        self.client = client
        self.template = Path('core/template.xml')
        self.filename = self.template.with_name("xml_test.xml")

        self.tree = parse(self.template)
        self.root = self.tree.getroot()
        self.now = datetime.now()

        self.fake_date()
        self.fake_emisor()

        self.save()

    def fake_date(self):
        formatted = self.now.strftime("%Y-%m-%dT%H:%M:%S")
        self.root.set('Fecha', formatted)

    def fake_emisor(self):
        receptor = self.root.find("cfdi:Emisor", XmlFile.ns)
        receptor.set('Rfc', self.client.rfc)

    def save(self):
        tree = ElementTree(self.root)
        tree.write(self.filename, encoding="utf-8", xml_declaration=True)

    def __call__(self):
        return self.filename

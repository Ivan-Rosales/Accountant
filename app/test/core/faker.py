import random
import uuid
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import ElementTree, parse

from execution.xml_file import XmlFile


class XmlFileFaker:
    def __init__(self, client, receptor=None, date=None):
        self.client = client
        self.receptor = receptor

        path = Path(__file__)
        self.template = path.with_name("template.xml")
        self.filename = path.with_name("xml_test.xml")

        self.tree = parse(self.template)
        self.root = self.tree.getroot()
        self.date = date or datetime.now()

        self.fake_root()
        self.fake_emisor()
        self.fake_receptor()
        self.fake_complemento()

        self.save()

    def fake_root(self):
        formatted = self.date.strftime("%Y-%m-%dT%H:%M:%S")

        self.root.set('Fecha', formatted)
        self.root.set('Total', str(round(random.uniform(1, 1000), 2)))

    def fake_emisor(self):
        receptor = self.root.find("cfdi:Emisor", XmlFile.ns)
        receptor.set('Rfc', self.client.rfc)
        receptor.set('Nombre', self.client.nombre)

    def fake_receptor(self):
        if self.receptor is None: return
        receptor = self.root.find("cfdi:Receptor", XmlFile.ns)
        receptor.set('Rfc', self.receptor.rfc)
        receptor.set('Nombre', self.receptor.nombre)

    def fake_complemento(self):
        timbre = self.root.find("cfdi:Complemento/tfd:TimbreFiscalDigital", XmlFile.ns)
        timbre.set('UUID', str(uuid.uuid4()))

    def save(self):
        tree = ElementTree(self.root)
        tree.write(self.filename, encoding="utf-8", xml_declaration=True)

    def __call__(self):
        return self.filename

from datetime import datetime
from functools import cached_property
from xml.etree.ElementTree import parse, Element


class XmlNode:
    def __init__(self, element):
        self.element: Element = element

    @cached_property
    def rfc(self):
        return self.element.attrib.get('Rfc')


class XmlFile:
    ns = {
        "cfdi": "http://www.sat.gob.mx/cfd/4"
    }

    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.tree = parse(self.xml_file)
        self.root = self.tree.getroot()

    @cached_property
    def emisor(self):
        return XmlNode(self.root.find(".//cfdi:Emisor", self.ns))

    @cached_property
    def receptor(self):
        return XmlNode(self.root.find(".//cfdi:Receptor", self.ns))

    @cached_property
    def date(self):
        str_date = self.root.attrib.get('Fecha')
        return datetime.fromisoformat(str_date)

    @cached_property
    def ieps(self):
        impuestos = self.root.find(".//cfdi:Impuestos", self.ns)
        traslados = impuestos.findall(".//cfdi:Traslados/cfdi:Traslado", self.ns)

        ieps = 0
        traslados_ieps = [i for i in traslados if i.attrib.get('Impuesto') == '003']
        for traslado_ieps in traslados_ieps:
            ieps += float(traslado_ieps.attrib.get('Importe', 0))

        return ieps

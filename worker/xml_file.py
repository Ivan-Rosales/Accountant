from datetime import datetime
from functools import cached_property
from xml.etree.ElementTree import parse, Element

from functions import decimal_property


class XmlNode:
    def __init__(self, element):
        self.element: Element = element

    @cached_property
    def rfc(self):
        return self.element.attrib.get('Rfc')

    @cached_property
    def name(self):
        return self.element.attrib.get('Nombre', '')


class XmlFile:
    ns = {
        "cfdi": "http://www.sat.gob.mx/cfd/4",
        "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
    }

    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.tree = parse(self.xml_file)
        self.root = self.tree.getroot()

    @cached_property
    def uuid(self):
        timbre = self.root.find("cfdi:Complemento/tfd:TimbreFiscalDigital", self.ns)
        return timbre.attrib.get('UUID')

    @cached_property
    def tipo(self):
        return self.root.attrib.get('TipoDeComprobante')

    @cached_property
    def emisor(self):
        return XmlNode(self.root.find("cfdi:Emisor", self.ns))

    @cached_property
    def receptor(self):
        return XmlNode(self.root.find("cfdi:Receptor", self.ns))

    @cached_property
    def date(self):
        str_date = self.root.attrib.get('Fecha')
        return datetime.fromisoformat(str_date)

    @cached_property
    @decimal_property
    def total(self):
        return float(self.root.attrib.get('Total', 0))

    @cached_property
    def impuestos(self):
        return self.root.find("cfdi:Impuestos", self.ns)

    @cached_property
    def traslados(self):
        if self.impuestos is None: return []
        return self.impuestos.findall("cfdi:Traslados/cfdi:Traslado", self.ns)

    @cached_property
    @decimal_property
    def iva(self):
        traslados_ieps = [i for i in self.traslados if i.attrib.get('Impuesto') == '002']
        return sum(float(i.attrib.get('Importe', 0)) for i in traslados_ieps)

    @cached_property
    @decimal_property
    def ieps(self):
        traslados_ieps = [i for i in self.traslados if i.attrib.get('Impuesto') == '003']
        return sum(float(i.attrib.get('Importe', 0)) for i in traslados_ieps)

    @cached_property
    def retenciones(self):
        if self.impuestos is None: return []
        return self.impuestos.findall("cfdi:Retenciones/cfdi:Retencion", self.ns)

    @cached_property
    @decimal_property
    def ret_iva(self):
        retenciones_iva = [i for i in self.retenciones if i.attrib.get('Impuesto') == '002']
        return sum(float(i.attrib.get('Importe', 0)) for i in retenciones_iva)

    @cached_property
    @decimal_property
    def ret_isr(self):
        retenciones_iva = [i for i in self.retenciones if i.attrib.get('Impuesto') == '001']
        return sum(float(i.attrib.get('Importe', 0)) for i in retenciones_iva)

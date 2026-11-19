"""Lectura de CFDI 3.2, 3.3 y 4.0.

Todos los importes se exponen en pesos (MXN): si el comprobante viene en otra moneda se
multiplican por TipoCambio. Los cálculos se hacen con Decimal a partir del texto del XML
(sin pasar por float) y se redondean a centavos solo al final.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import cached_property
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import parse

from exceptions import XmlDataException
from functions import normalize_number

CFDI_NAMESPACES = {
    'http://www.sat.gob.mx/cfd/4': '4.0',
    'http://www.sat.gob.mx/cfd/3': '3.x',
}
TFD_NS = 'http://www.sat.gob.mx/TimbreFiscalDigital'
IMPLOCAL_NS = 'http://www.sat.gob.mx/implocal'
NOMINA12_NS = 'http://www.sat.gob.mx/nomina12'
NOMINA11_NS = 'http://www.sat.gob.mx/nomina'

IVA, IEPS, ISR = '002', '003', '001'
IMPUESTO_32 = {'IVA': IVA, 'IEPS': IEPS, 'ISR': ISR}
TIPO_32 = {'ingreso': 'I', 'egreso': 'E', 'traslado': 'T'}
ZERO = Decimal(0)


def to_decimal(value, default=ZERO) -> Decimal:
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value).strip())
    except InvalidOperation:
        raise XmlDataException(f'Importe inválido en el XML: {value!r}')


class XmlNode:
    def __init__(self, element):
        self.element: Element | None = element

    def _attr(self, *names, default=''):
        if self.element is None: return default
        for name in names:
            value = self.element.attrib.get(name)
            if value is not None: return value
        return default

    @cached_property
    def rfc(self):
        return (self._attr('Rfc', 'rfc') or '').strip().upper()

    @cached_property
    def name(self):
        return self._attr('Nombre', 'nombre')

    def __eq__(self, other):
        return self.rfc == other.rfc

    def __hash__(self):
        return hash(self.rfc)


class XmlFile:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        try:
            self.tree = parse(self.xml_file)
        except Exception as error:
            raise XmlDataException(f'No se pudo leer el XML {xml_file}: {error}') from error
        self.root = self.tree.getroot()

        namespace = self.root.tag[1:].split('}')[0] if self.root.tag.startswith('{') else ''
        if namespace not in CFDI_NAMESPACES or not self.root.tag.endswith('Comprobante'):
            raise XmlDataException(f'El archivo no es un CFDI: {xml_file}')

        self.ns = {'cfdi': namespace, 'tfd': TFD_NS, 'implocal': IMPLOCAL_NS}

    # ---- atributos básicos ---------------------------------------------------
    def attr(self, *names, default=None):
        for name in names:
            value = self.root.attrib.get(name)
            if value is not None: return value
        return default

    @cached_property
    def version(self):
        return self.attr('Version', 'version', default='')

    @cached_property
    def is_v32(self):
        return self.version.startswith('3.2') or 'version' in self.root.attrib

    @cached_property
    def uuid(self):
        timbre = self.root.find('cfdi:Complemento/tfd:TimbreFiscalDigital', self.ns)
        if timbre is None or not timbre.attrib.get('UUID'):
            raise XmlDataException(f'El CFDI no está timbrado (sin UUID): {self.xml_file}')
        return timbre.attrib['UUID'].upper()

    @cached_property
    def tipo(self):
        tipo = self.attr('TipoDeComprobante', 'tipoDeComprobante', default='')
        return TIPO_32.get(tipo.lower(), tipo) if self.is_v32 else tipo

    @cached_property
    def emisor(self):
        return XmlNode(self.root.find('cfdi:Emisor', self.ns))

    @cached_property
    def receptor(self):
        return XmlNode(self.root.find('cfdi:Receptor', self.ns))

    @cached_property
    def date(self):
        str_date = self.attr('Fecha', 'fecha')
        if str_date is None: raise XmlDataException('cfdi:Comprobante has not attribute Fecha')
        return datetime.fromisoformat(str_date[:19])

    @cached_property
    def moneda(self):
        return (self.attr('Moneda', default='MXN') or 'MXN').upper()

    @cached_property
    def tipo_cambio(self) -> Decimal:
        """Factor para convertir a pesos. MXN y XXX (pagos) valen 1."""
        if self.moneda in ('MXN', 'XXX', 'PESOS', 'MN', 'PESO MEXICANO'):
            return Decimal(1)
        rate = to_decimal(self.attr('TipoCambio'), default=None)
        if rate is None or rate <= 0:
            raise XmlDataException(f'CFDI en {self.moneda} sin TipoCambio: {self.uuid}')
        return rate

    def mxn(self, value: Decimal) -> Decimal:
        return normalize_number(value * self.tipo_cambio)

    # ---- importes del comprobante -------------------------------------------
    @cached_property
    def total(self):
        return self.mxn(to_decimal(self.attr('Total', 'total')))

    @cached_property
    def subtotal(self):
        return self.mxn(to_decimal(self.attr('SubTotal', 'subTotal')))

    @cached_property
    def descuento(self):
        return self.mxn(to_decimal(self.attr('Descuento', 'descuento')))

    @cached_property
    def impuestos(self):
        # Solo el nodo global (hijo directo del comprobante), nunca el de un concepto o complemento
        return self.root.find('cfdi:Impuestos', self.ns)

    def _tax_rows(self, kind):
        if self.impuestos is None: return []
        tag = 'Traslados/cfdi:Traslado' if kind == 'traslado' else 'Retenciones/cfdi:Retencion'
        return self.impuestos.findall(f'cfdi:{tag}', self.ns)

    def _impuesto(self, element):
        value = element.attrib.get('Impuesto') or element.attrib.get('impuesto') or ''
        return IMPUESTO_32.get(value.upper(), value)

    def _sum(self, kind, impuesto):
        total = sum((to_decimal(e.attrib.get('Importe', e.attrib.get('importe')))
                     for e in self._tax_rows(kind) if self._impuesto(e) == impuesto), ZERO)
        return self.mxn(total)

    @cached_property
    def traslados(self):
        return self._tax_rows('traslado')

    @cached_property
    def retenciones(self):
        return self._tax_rows('retencion')

    @cached_property
    def iva(self):
        return self._sum('traslado', IVA)

    @cached_property
    def ieps(self):
        return self._sum('traslado', IEPS)

    @cached_property
    def ret_iva(self):
        return self._sum('retencion', IVA)

    @cached_property
    def ret_isr(self):
        return self._sum('retencion', ISR)

    @cached_property
    def local_traslados(self):
        node = self.root.find('cfdi:Complemento/implocal:ImpuestosLocales', self.ns)
        if node is None: return ZERO
        return self.mxn(to_decimal(node.attrib.get('TotaldeTraslados')))

    @cached_property
    def local_retenciones(self):
        node = self.root.find('cfdi:Complemento/implocal:ImpuestosLocales', self.ns)
        if node is None: return ZERO
        return self.mxn(to_decimal(node.attrib.get('TotaldeRetenciones')))

    # ---- nómina ------------------------------------------------------------
    @cached_property
    def percepciones(self):
        """Percepciones brutas de un CFDI de nómina (antes de ISR retenido, IMSS y demás deducciones).

        Nómina 1.2: atributo TotalPercepciones. Nómina 1.1 o sin el atributo: TotalGravado + TotalExento
        de cfdi:Percepciones. Si no hay complemento se usa SubTotal.
        """
        for prefix, uri in (('n12', NOMINA12_NS), ('n11', NOMINA11_NS)):
            nomina = self.root.find(f'cfdi:Complemento/{prefix}:Nomina', self.ns | {prefix: uri})
            if nomina is None: continue
            if nomina.attrib.get('TotalPercepciones') is not None:
                return self.mxn(to_decimal(nomina.attrib['TotalPercepciones']))
            node = nomina.find(f'{prefix}:Percepciones', {prefix: uri})
            if node is not None:
                return self.mxn(to_decimal(node.attrib.get('TotalGravado')) + to_decimal(node.attrib.get('TotalExento')))
        return self.subtotal

    # ---- desglose por tasa de IVA (valor de actos, sin impuestos) -----------
    @cached_property
    def bases(self) -> dict:
        """Importe neto de los conceptos clasificado por su tratamiento de IVA.

        Claves: 'tasa16', 'tasa8', 'tasa0', 'exento', 'no_objeto' (otras tasas van a 'tasa_otra').
        Se calcula por concepto (Importe - Descuento) para que la suma cuadre con SubTotal - Descuento.
        """
        result = {k: ZERO for k in ('tasa16', 'tasa8', 'tasa0', 'tasa_otra', 'exento', 'no_objeto')}
        conceptos = self.root.findall('cfdi:Conceptos/cfdi:Concepto', self.ns)

        if self.is_v32 or not conceptos:
            # CFDI 3.2 no tiene impuestos por concepto: se clasifica con el nodo global
            neto = to_decimal(self.attr('subTotal', 'SubTotal')) - to_decimal(self.attr('descuento', 'Descuento'))
            rates = [to_decimal(e.attrib.get('tasa', e.attrib.get('TasaOCuota'))) for e in self.traslados
                     if self._impuesto(e) == IVA]
            key = 'no_objeto' if not rates else self._rate_key(max(rates) / (100 if max(rates) > 1 else 1))
            result[key] = neto
            return {k: self.mxn(v) for k, v in result.items()}

        for concepto in conceptos:
            neto = to_decimal(concepto.attrib.get('Importe')) - to_decimal(concepto.attrib.get('Descuento'))
            ivas = [e for e in concepto.findall('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', self.ns)
                    if self._impuesto(e) == IVA]
            if not ivas:
                result['no_objeto'] += neto
            elif any(e.attrib.get('TipoFactor') == 'Exento' for e in ivas):
                result['exento'] += neto
            else:
                rate = max(to_decimal(e.attrib.get('TasaOCuota')) for e in ivas)
                result[self._rate_key(rate)] += neto

        return {k: self.mxn(v) for k, v in result.items()}

    @staticmethod
    def _rate_key(rate: Decimal) -> str:
        if rate == Decimal('0.16'): return 'tasa16'
        if rate == Decimal('0.08'): return 'tasa8'
        if rate == 0: return 'tasa0'
        return 'tasa_otra'

    @cached_property
    def gravado(self):
        """Valor de actos gravados con IVA a tasa mayor a 0."""
        b = self.bases
        return b['tasa16'] + b['tasa8'] + b['tasa_otra']

    @cached_property
    def no_gravado(self):
        """Valor de actos a tasa 0, exentos o no objeto de IVA."""
        b = self.bases
        return b['tasa0'] + b['exento'] + b['no_objeto']

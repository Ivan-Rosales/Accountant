"""Corpus de CFDI sintéticos que cubre los casos fiscales que el sistema debe soportar.

`expected` son los valores que DEBERÍA leer el parser (en pesos MXN). Los casos marcados
con `phase1` documentan defectos conocidos que se corrigen en la Fase 1; sus pruebas
están en xfail estricto para que avisen en cuanto queden resueltos.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal as D

from tests.cfdi_builder import Cfdi, Concepto, Traslado, Retencion, IVA, IEPS, ISR

CLIENTE_RFC = 'AAA010101AAA'
PROVEEDOR_RFC = 'BBB020202BBB'
PERSONA_FISICA_RFC = 'CACX760510AB1'
FECHA = datetime(2025, 1, 15, 12, 0, 0)


@dataclass
class Case:
    id: str
    cfdi: Cfdi
    expected: dict
    phase1: str | None = None  # motivo del xfail
    legacy_ok: bool = True  # el programa anterior lo lee bien
    tags: set = field(default_factory=set)


def _cfdi(**kw):
    base = dict(emisor_rfc=CLIENTE_RFC, receptor_rfc=PROVEEDOR_RFC, fecha=FECHA)
    return Cfdi(**(base | kw))


def _exp(total, iva=0, ieps=0, ret_iva=0, ret_isr=0, tipo='I'):
    return dict(tipo=tipo, total=D(str(total)), iva=D(str(iva)), ieps=D(str(ieps)),
                ret_iva=D(str(ret_iva)), ret_isr=D(str(ret_isr)))


CASES = [
    Case('v40_iva16', _cfdi(conceptos=[Concepto(1000)]), _exp(1160, iva=160)),
    Case('v40_iva16_varios_conceptos',
         _cfdi(conceptos=[Concepto(100), Concepto(250.50), Concepto(0.99)]),
         _exp(407.73, iva=56.24)),
    Case('v40_ieps_iva',
         _cfdi(conceptos=[Concepto(500, traslados=[Traslado(IEPS, '0.080000'), Traslado(IVA, '0.160000', base=D(540))]),
                          Concepto(200, traslados=[Traslado(IVA, '0.000000')])]),
         _exp(826.40, iva=86.40, ieps=40)),
    Case('v40_honorarios_retenciones',
         _cfdi(emisor_rfc=PERSONA_FISICA_RFC, receptor_rfc=CLIENTE_RFC,
               conceptos=[Concepto(10000, retenciones=[Retencion(IVA, '0.106667'), Retencion(ISR, '0.100000')])]),
         _exp(9533.33, iva=1600, ret_iva=1066.67, ret_isr=1000)),
    Case('v40_ieps_y_retenciones',
         _cfdi(conceptos=[Concepto(1000, traslados=[Traslado(IEPS, '0.080000'), Traslado(IVA, '0.160000', base=D(1080))],
                                   retenciones=[Retencion(ISR, '0.012500')])]),
         _exp(1240.30, iva=172.80, ieps=80, ret_isr=12.50)),
    Case('v40_frontera_8',
         _cfdi(conceptos=[Concepto(1000, traslados=[Traslado(IVA, '0.080000')])]),
         _exp(1080, iva=80), tags={'tasa8'}),
    Case('v40_exento',
         _cfdi(conceptos=[Concepto(1000, traslados=[Traslado(IVA, None)])]),
         _exp(1000), tags={'exento'}),
    Case('v40_descuento',
         _cfdi(descuento=D(100), conceptos=[Concepto(1000, traslados=[Traslado(IVA, '0.160000', base=D(900))])]),
         _exp(1044, iva=144)),
    Case('v40_nota_credito', _cfdi(tipo='E', conceptos=[Concepto(100)]), _exp(116, iva=16, tipo='E')),
    Case('v40_pago', _cfdi(tipo='P', conceptos=[Concepto(0, traslados=[])]), _exp(0, tipo='P')),
    Case('v40_nomina', _cfdi(tipo='N', conceptos=[Concepto(5000, traslados=[])]), _exp(5000, tipo='N')),
    Case('v40_usd',
         _cfdi(moneda='USD', tipo_cambio=D('17.5000'), conceptos=[Concepto(100)]),
         _exp(2030, iva=280),
         phase1='No convierte con TipoCambio: suma USD como si fueran pesos', legacy_ok=False),
    Case('v33_iva16', _cfdi(version='3.3', conceptos=[Concepto(1000)]), _exp(1160, iva=160),
         phase1='Solo lee el namespace de CFDI 4.0'),
    Case('v33_honorarios_retenciones',
         _cfdi(version='3.3', emisor_rfc=PERSONA_FISICA_RFC, receptor_rfc=CLIENTE_RFC,
               conceptos=[Concepto(10000, retenciones=[Retencion(IVA, '0.106667'), Retencion(ISR, '0.100000')])]),
         _exp(9533.33, iva=1600, ret_iva=1066.67, ret_isr=1000),
         phase1='Solo lee el namespace de CFDI 4.0'),
    Case('v32_iva16', _cfdi(version='3.2', conceptos=[Concepto(1000)]), _exp(1160, iva=160),
         phase1='No soporta CFDI 3.2 (atributos en minúscula)'),
]

CASES_BY_ID = {c.id: c for c in CASES}

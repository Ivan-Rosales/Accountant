"""Generador de CFDI sintéticos para pruebas.

Produce XML con la misma forma que los CFDI reales (3.2, 3.3 y 4.0) pero con datos
inventados, para no versionar facturas reales de clientes en el repositorio.
Los montos se calculan con Decimal a partir de los conceptos, igual que un PAC.
"""
import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.sax.saxutils import quoteattr

IVA, IEPS, ISR = '002', '003', '001'
CENT = Decimal('0.01')

NAMESPACES = {
    '3.2': 'http://www.sat.gob.mx/cfd/3',
    '3.3': 'http://www.sat.gob.mx/cfd/3',
    '4.0': 'http://www.sat.gob.mx/cfd/4',
}
TIPO_32 = {'I': 'ingreso', 'E': 'egreso', 'T': 'traslado'}
IMPUESTO_32 = {IVA: 'IVA', IEPS: 'IEPS', ISR: 'ISR'}


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Traslado:
    impuesto: str = IVA
    tasa: str | None = '0.160000'  # None => TipoFactor Exento
    base: Decimal | None = None  # None => importe del concepto

    @property
    def exento(self):
        return self.tasa is None


@dataclass
class Retencion:
    impuesto: str
    tasa: str
    base: Decimal | None = None


@dataclass
class Concepto:
    importe: Decimal
    traslados: list = field(default_factory=lambda: [Traslado()])
    retenciones: list = field(default_factory=list)
    descripcion: str = 'CONCEPTO DE PRUEBA'

    def __post_init__(self):
        self.importe = money(self.importe)


@dataclass
class DoctoPagado:
    uuid: str
    imp_pagado: Decimal
    bases: dict = field(default_factory=dict)  # {'0.160000': base}
    moneda: str = 'MXN'
    equivalencia: str = '1'


@dataclass
class Pago:
    fecha: datetime
    documentos: list
    moneda: str = 'MXN'
    tipo_cambio: str = '1'


@dataclass
class Cfdi:
    emisor_rfc: str
    receptor_rfc: str
    conceptos: list
    fecha: datetime = datetime(2025, 1, 15, 12, 0, 0)
    tipo: str = 'I'
    version: str = '4.0'
    emisor_nombre: str = 'EMISOR DE PRUEBA'
    receptor_nombre: str = 'RECEPTOR DE PRUEBA'
    descuento: Decimal = Decimal(0)
    moneda: str = 'MXN'
    tipo_cambio: Decimal | None = None
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()).upper())
    metodo_pago: str | None = None  # 'PUE' / 'PPD'
    pagos: list = field(default_factory=list)  # para tipo P: list[Pago]
    pagos_version: str = '2.0'

    # ---- cálculos -------------------------------------------------------
    @property
    def subtotal(self):
        return sum((c.importe for c in self.conceptos), Decimal(0))

    def _traslados(self):
        for c in self.conceptos:
            for t in c.traslados:
                base = money(t.base if t.base is not None else c.importe)
                importe = None if t.exento else money(base * Decimal(t.tasa))
                yield t, base, importe

    def _retenciones(self):
        for c in self.conceptos:
            for r in c.retenciones:
                base = money(r.base if r.base is not None else c.importe)
                yield r, base, money(base * Decimal(r.tasa))

    @property
    def total_trasladados(self):
        return sum((i for *_, i in self._traslados() if i is not None), Decimal(0))

    @property
    def total_retenidos(self):
        return sum((i for *_, i in self._retenciones()), Decimal(0))

    @property
    def total(self):
        if self.tipo in ('P', 'T'):
            return Decimal(0)
        return money(self.subtotal - money(self.descuento) + self.total_trasladados - self.total_retenidos)

    def tax_total(self, impuesto, retenido=False):
        items = self._retenciones() if retenido else self._traslados()
        return sum((i for t, _, i in items if t.impuesto == impuesto and i is not None), Decimal(0))

    # ---- serialización --------------------------------------------------
    def to_xml(self) -> str:
        if self.version == '3.2':
            return self._to_xml_32()
        return self._to_xml_33_40()

    def _attrs(self, **attrs):
        return ' '.join(f'{k}={quoteattr(str(v))}' for k, v in attrs.items() if v is not None)

    def _group(self, kind, rows):
        if not rows:
            return ''
        tag = 'Traslado' if kind == 'Traslados' else 'Retencion'
        inner = ''.join(f'<cfdi:{tag} {self._attrs(**r)}/>' for r in rows)
        return f'<cfdi:{kind}>{inner}</cfdi:{kind}>'

    def _to_xml_33_40(self):
        v4 = self.version == '4.0'
        is_pago = self.tipo == 'P'
        conceptos = ''
        for n, c in enumerate(self.conceptos):
            # Como en un CFDI real, el descuento global es la suma de los descuentos por concepto
            desc = {'Descuento': money(self.descuento)} if self.descuento and n == 0 else {}
            tras = []
            for t in c.traslados:
                base = money(t.base if t.base is not None else c.importe)
                row = {'Base': base, 'Impuesto': t.impuesto, 'TipoFactor': 'Exento' if t.exento else 'Tasa'}
                if not t.exento:
                    row |= {'TasaOCuota': t.tasa, 'Importe': money(base * Decimal(t.tasa))}
                tras.append(row)
            rets = [{'Base': money(r.base if r.base is not None else c.importe), 'Impuesto': r.impuesto,
                     'TipoFactor': 'Tasa', 'TasaOCuota': r.tasa,
                     'Importe': money(money(r.base if r.base is not None else c.importe) * Decimal(r.tasa))}
                    for r in c.retenciones]
            imp = ''
            if tras or rets:
                imp = f'<cfdi:Impuestos>{self._group("Traslados", tras)}{self._group("Retenciones", rets)}</cfdi:Impuestos>'
            obj = {'ObjetoImp': '02' if (tras or rets) else '01'} if v4 else {}
            conceptos += (f'<cfdi:Concepto {self._attrs(ClaveProdServ="01010101", Cantidad="1", ClaveUnidad="E48", Descripcion=c.descripcion, ValorUnitario=c.importe, Importe=c.importe, **desc, **obj)}>'
                          f'{imp}</cfdi:Concepto>')

        # Impuestos globales: agrupados por impuesto/tasa como lo hace el PAC
        impuestos = ''
        if not is_pago and self.tipo != 'N':
            grouped = {}
            for t, base, importe in self._traslados():
                key = (t.impuesto, t.tasa)
                b, i = grouped.get(key, (Decimal(0), Decimal(0)))
                grouped[key] = (b + base, i + (importe or 0))
            tras = []
            for (imp_, tasa), (base, importe) in grouped.items():
                row = {'Base': base} if v4 else {}
                row |= {'Impuesto': imp_, 'TipoFactor': 'Exento' if tasa is None else 'Tasa'}
                if tasa is not None:
                    row |= {'TasaOCuota': tasa, 'Importe': money(importe)}
                tras.append(row)
            ret_grouped = {}
            for r, _, importe in self._retenciones():
                ret_grouped[r.impuesto] = ret_grouped.get(r.impuesto, Decimal(0)) + importe
            rets = [{'Impuesto': k, 'Importe': money(v)} for k, v in ret_grouped.items()]
            if tras or rets:
                attrs = {}
                if rets: attrs['TotalImpuestosRetenidos'] = money(self.total_retenidos)
                if any(r.get('Importe') is not None for r in tras):
                    attrs['TotalImpuestosTrasladados'] = money(self.total_trasladados)
                impuestos = (f'<cfdi:Impuestos {self._attrs(**attrs)}>'
                             f'{self._group("Retenciones", rets)}{self._group("Traslados", tras)}</cfdi:Impuestos>')

        regimen = {'RegimenFiscal': '601'}
        receptor_extra = {'UsoCFDI': 'G03'}
        if v4:
            receptor_extra |= {'DomicilioFiscalReceptor': '01000', 'RegimenFiscalReceptor': '601'}
        ns = NAMESPACES[self.version]
        moneda = 'XXX' if is_pago else self.moneda
        root = self._attrs(
            Version=self.version, Fecha=self.fecha.strftime('%Y-%m-%dT%H:%M:%S'),
            SubTotal=money(0 if is_pago else self.subtotal),
            Descuento=money(self.descuento) if self.descuento else None,
            Moneda=moneda, TipoCambio=self.tipo_cambio, Total=money(self.total),
            TipoDeComprobante=self.tipo, MetodoPago=self.metodo_pago, LugarExpedicion='01000',
            Exportacion='01' if v4 else None,
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<cfdi:Comprobante xmlns:cfdi="{ns}" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" {root}>'
            f'<cfdi:Emisor {self._attrs(Rfc=self.emisor_rfc, Nombre=self.emisor_nombre, **regimen)}/>'
            f'<cfdi:Receptor {self._attrs(Rfc=self.receptor_rfc, Nombre=self.receptor_nombre, **receptor_extra)}/>'
            f'<cfdi:Conceptos>{conceptos}</cfdi:Conceptos>'
            f'{impuestos}'
            f'<cfdi:Complemento>{self._nomina()}{self._pagos()}<tfd:TimbreFiscalDigital Version="1.1" UUID="{self.uuid}" '
            f'FechaTimbrado="{self.fecha.strftime("%Y-%m-%dT%H:%M:%S")}"/></cfdi:Complemento>'
            '</cfdi:Comprobante>'
        )

    def _pagos(self):
        """Complemento de pagos 2.0 (con ImpuestosDR) o 1.0 (sin desglose)."""
        if self.tipo != 'P' or not self.pagos: return ''
        v2 = self.pagos_version == '2.0'
        prefix, uri = ('pago20', 'http://www.sat.gob.mx/Pagos20') if v2 else ('pago10', 'http://www.sat.gob.mx/Pagos')
        body = ''
        for pago in self.pagos:
            docs = ''
            for d in pago.documentos:
                attrs = {'IdDocumento': d.uuid, 'MonedaDR': d.moneda, 'NumParcialidad': '1',
                         'ImpSaldoAnt': money(d.imp_pagado), 'ImpPagado': money(d.imp_pagado), 'ImpSaldoInsoluto': '0.00'}
                impuestos = ''
                if v2:
                    attrs |= {'EquivalenciaDR': d.equivalencia, 'ObjetoImpDR': '02'}
                    tras = ''.join(f'<{prefix}:TrasladoDR BaseDR="{money(b)}" ImpuestoDR="002" TipoFactorDR="Tasa" '
                                   f'TasaOCuotaDR="{t}" ImporteDR="{money(b * Decimal(t))}"/>' for t, b in d.bases.items())
                    impuestos = f'<{prefix}:ImpuestosDR><{prefix}:TrasladosDR>{tras}</{prefix}:TrasladosDR></{prefix}:ImpuestosDR>'
                elif d.moneda != 'MXN':
                    attrs['TipoCambioDR'] = d.equivalencia
                docs += f'<{prefix}:DoctoRelacionado {self._attrs(**attrs)}>{impuestos}</{prefix}:DoctoRelacionado>'
            p_attrs = {'FechaPago': pago.fecha.strftime('%Y-%m-%dT%H:%M:%S'), 'FormaDePagoP': '03', 'MonedaP': pago.moneda,
                       'Monto': money(sum(d.imp_pagado for d in pago.documentos))}
            if v2: p_attrs['TipoCambioP'] = pago.tipo_cambio
            elif pago.moneda != 'MXN': p_attrs['TipoCambioP'] = pago.tipo_cambio
            body += f'<{prefix}:Pago {self._attrs(**p_attrs)}>{docs}</{prefix}:Pago>'
        return f'<{prefix}:Pagos xmlns:{prefix}="{uri}" Version="{self.pagos_version}">{body}</{prefix}:Pagos>'

    def _nomina(self):
        """Complemento de nómina 1.2: percepciones = importe del concepto, deducciones = descuento."""
        if self.tipo != 'N': return ''
        return (
            '<nomina12:Nomina xmlns:nomina12="http://www.sat.gob.mx/nomina12" Version="1.2" TipoNomina="O" '
            f'TotalPercepciones="{money(self.subtotal)}" TotalDeducciones="{money(self.descuento)}">'
            f'<nomina12:Percepciones TotalSueldos="{money(self.subtotal)}" TotalGravado="{money(self.subtotal)}" TotalExento="0.00"/>'
            '</nomina12:Nomina>'
        )

    def _to_xml_32(self):
        ns = NAMESPACES['3.2']
        conceptos = ''.join(
            f'<cfdi:Concepto {self._attrs(cantidad="1", unidad="SERVICIO", descripcion=c.descripcion, valorUnitario=c.importe, importe=c.importe)}/>'
            for c in self.conceptos)
        tras = [{'impuesto': IMPUESTO_32[t.impuesto], 'tasa': f'{Decimal(t.tasa) * 100:.2f}', 'importe': i}
                for t, _, i in self._traslados() if i is not None]
        rets = [{'impuesto': IMPUESTO_32[r.impuesto], 'importe': i} for r, _, i in self._retenciones()]
        attrs = {'totalImpuestosTrasladados': money(self.total_trasladados)}
        if rets: attrs['totalImpuestosRetenidos'] = money(self.total_retenidos)
        root = self._attrs(
            version='3.2', fecha=self.fecha.strftime('%Y-%m-%dT%H:%M:%S'), subTotal=money(self.subtotal),
            descuento=money(self.descuento) if self.descuento else None, Moneda=self.moneda,
            TipoCambio=self.tipo_cambio, total=money(self.total), tipoDeComprobante=TIPO_32.get(self.tipo, 'ingreso'),
            formaDePago='PAGO EN UNA SOLA EXHIBICION', metodoDePago='99', LugarExpedicion='MEXICO',
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<cfdi:Comprobante xmlns:cfdi="{ns}" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" {root}>'
            f'<cfdi:Emisor {self._attrs(rfc=self.emisor_rfc, nombre=self.emisor_nombre)}/>'
            f'<cfdi:Receptor {self._attrs(rfc=self.receptor_rfc, nombre=self.receptor_nombre)}/>'
            f'<cfdi:Conceptos>{conceptos}</cfdi:Conceptos>'
            f'<cfdi:Impuestos {self._attrs(**attrs)}>{self._group("Retenciones", rets)}{self._group("Traslados", tras)}</cfdi:Impuestos>'
            f'<cfdi:Complemento><tfd:TimbreFiscalDigital version="1.0" UUID="{self.uuid}" '
            f'FechaTimbrado="{self.fecha.strftime("%Y-%m-%dT%H:%M:%S")}"/></cfdi:Complemento>'
            '</cfdi:Comprobante>'
        )

    def write(self, folder: Path, name: str | None = None) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{name or self.uuid}.xml'
        path.write_text(self.to_xml(), encoding='utf-8')
        return path

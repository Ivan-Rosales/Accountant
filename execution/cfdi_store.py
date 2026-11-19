"""Persistencia de CFDI por cliente: guardar lo leído de los ZIP y consultar por periodo."""
from typing import Iterable

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import Session

from execution.xml_file import XmlFile
from models import Cliente, Comprobante


def _values(client: Cliente, xml: XmlFile, origen: str | None) -> dict:
    bases = xml.bases
    return dict(
        cliente_id=client.id,
        uuid=xml.uuid,
        ingreso=xml.emisor.rfc == client.rfc,
        tipo=xml.tipo,
        version=xml.version,
        fecha=xml.date,
        year=xml.date.year,
        month=xml.date.month,
        emisor_rfc=xml.emisor.rfc,
        emisor_nombre=xml.emisor.name,
        receptor_rfc=xml.receptor.rfc,
        receptor_nombre=xml.receptor.name,
        moneda=xml.moneda,
        tipo_cambio=xml.tipo_cambio,
        total=xml.total,
        iva=xml.iva,
        ieps=xml.ieps,
        ret_iva=xml.ret_iva,
        ret_isr=xml.ret_isr,
        gravado=xml.gravado,
        no_gravado=xml.no_gravado,
        base_tasa16=bases['tasa16'],
        base_tasa8=bases['tasa8'],
        base_tasa0=bases['tasa0'],
        base_exento=bases['exento'],
        base_no_objeto=bases['no_objeto'],
        percepciones=xml.percepciones if xml.tipo == 'N' else None,
        metodo_pago=xml.metodo_pago,
        origen=origen,
    )


def save_xml_files(session: Session, client: Cliente, xml_files: Iterable[XmlFile], origen=None) -> dict:
    """Inserta o actualiza (por UUID) los CFDI del cliente. Conserva la marca de cancelado.

    Devuelve {'nuevos': n, 'actualizados': n}.
    """
    xml_files = list(xml_files)
    uuids = [x.uuid for x in xml_files]
    existing = {c.uuid: c for c in session.scalars(
        select(Comprobante).where(Comprobante.cliente_id == client.id, Comprobante.uuid.in_(uuids)))}

    stats = {'nuevos': 0, 'actualizados': 0}
    for xml in xml_files:
        values = _values(client, xml, origen)
        if (record := existing.get(xml.uuid)) is None:
            session.add(Comprobante(**values))
            stats['nuevos'] += 1
        else:
            for key, value in values.items():
                setattr(record, key, value)
            stats['actualizados'] += 1

    _save_payments(session, client, [x for x in xml_files if x.tipo == 'P'])
    session.commit()
    return stats


def _save_payments(session: Session, client: Cliente, xml_files):
    from models import PagoDocumento
    if not xml_files: return
    session.execute(delete(PagoDocumento).where(PagoDocumento.cliente_id == client.id,
                                                PagoDocumento.pago_uuid.in_([x.uuid for x in xml_files])))
    for xml in xml_files:
        for pago in xml.pagos:
            session.add(PagoDocumento(
                cliente_id=client.id, pago_uuid=xml.uuid, ingreso=xml.emisor.rfc == client.rfc,
                year=pago['fecha_pago'].year, month=pago['fecha_pago'].month,
                emisor_rfc=xml.emisor.rfc, emisor_nombre=xml.emisor.name, **pago,
            ))


def month_records(session: Session, client: Cliente, year: int, month: int, ingreso: bool,
                  include_cancelled=False) -> list[Comprobante]:
    if ingreso:
        kind = and_(Comprobante.ingreso.is_(True), Comprobante.tipo != 'N')
    else:
        # Las nóminas que emite el cliente (como patrón) son egresos
        kind = or_(Comprobante.ingreso.is_(False), and_(Comprobante.ingreso.is_(True), Comprobante.tipo == 'N'))
    query = select(Comprobante).where(
        Comprobante.cliente_id == client.id,
        Comprobante.year == year,
        Comprobante.month == month,
        kind,
    ).order_by(Comprobante.fecha, Comprobante.uuid)
    if not include_cancelled:
        query = query.where(Comprobante.cancelado.is_(False))
    return list(session.scalars(query))


def set_cancelled(session: Session, client: Cliente, uuid: str, cancelled=True) -> bool:
    record = session.scalar(select(Comprobante).where(Comprobante.cliente_id == client.id,
                                                      Comprobante.uuid == uuid.upper()))
    if record is None: return False
    record.cancelado = cancelled
    session.commit()
    return True


DIOT_FIELDS = ('tipo_tercero', 'tipo_operacion', 'frontera', 'tax_id', 'nombre_extranjero', 'pais', 'jurisdiccion')


def diot_settings(session: Session, client: Cliente) -> dict:
    from execution.diot import DiotSettings
    from models import ProveedorDiot
    rows = session.scalars(select(ProveedorDiot).where(ProveedorDiot.cliente_id == client.id))
    return {r.rfc: DiotSettings(**{f: getattr(r, f) or '' for f in DIOT_FIELDS}) for r in rows}


def save_diot_settings(session: Session, client: Cliente, providers) -> None:
    """Guarda lo capturado por proveedor para que la próxima DIOT se llene sola."""
    from models import ProveedorDiot
    existing = {r.rfc: r for r in session.scalars(select(ProveedorDiot).where(ProveedorDiot.cliente_id == client.id))}
    for p in providers:
        row = existing.get(p.rfc) or ProveedorDiot(cliente_id=client.id, rfc=p.rfc)
        for f in DIOT_FIELDS:
            setattr(row, f, getattr(p, f) or None)
        session.add(row)
    session.commit()


def received_records(session: Session, client: Cliente, year: int, month: int) -> list[Comprobante]:
    """CFDI recibidos (proveedores) del periodo, sin cancelados."""
    query = select(Comprobante).where(
        Comprobante.cliente_id == client.id, Comprobante.year == year, Comprobante.month == month,
        Comprobante.ingreso.is_(False), Comprobante.cancelado.is_(False),
    ).order_by(Comprobante.fecha)
    return list(session.scalars(query))


def cash_records(session: Session, client: Cliente, year: int, month: int) -> tuple[list, list]:
    """Movimientos con proveedores efectivamente pagados en el periodo (flujo de efectivo, para la DIOT).

    - Facturas PUE (o sin método) y notas de crédito: por la fecha de la factura.
    - Facturas PPD: por la fecha de pago de su complemento de pago (REP).
    Si el REP no trae el desglose de impuestos (Pagos 1.0), se prorratea con la factura pagada.

    Devuelve (movimientos, facturas PPD del periodo sin pago registrado).
    """
    from decimal import Decimal
    from models import PagoDocumento

    invoices = [r for r in received_records(session, client, year, month)]
    by_date = [r for r in invoices if not (r.tipo == 'I' and r.metodo_pago == 'PPD')]

    cancelled_payments = select(Comprobante.uuid).where(Comprobante.cliente_id == client.id,
                                                        Comprobante.cancelado.is_(True))
    payments = list(session.scalars(select(PagoDocumento).where(
        PagoDocumento.cliente_id == client.id, PagoDocumento.year == year, PagoDocumento.month == month,
        PagoDocumento.ingreso.is_(False), PagoDocumento.pago_uuid.not_in(cancelled_payments),
    ).order_by(PagoDocumento.fecha_pago)))

    documents = {c.uuid: c for c in session.scalars(select(Comprobante).where(
        Comprobante.cliente_id == client.id, Comprobante.uuid.in_([p.documento_uuid for p in payments])))}

    fields = ('base_tasa16', 'base_tasa8', 'base_tasa0', 'base_exento', 'base_no_objeto', 'ret_iva', 'ret_isr')
    for payment in payments:
        session.expunge(payment)  # se ajusta en memoria, no se guarda
        if payment.con_impuestos: continue
        invoice = documents.get(payment.documento_uuid)
        if invoice is not None and invoice.total:
            ratio = Decimal(payment.imp_pagado) / Decimal(invoice.total)
            for f in fields:
                setattr(payment, f, (getattr(invoice, f) or Decimal(0)) * ratio)
        else:
            # Sin desglose ni factura: se asume IVA 16 % y se avisa
            payment.base_tasa16 = Decimal(payment.imp_pagado) / Decimal('1.16')
            payment.aviso = f'Pago {payment.pago_uuid[:8]} sin desglose de impuestos ni factura: se asumió IVA 16 %'

    paid = {p.documento_uuid for p in session.scalars(select(PagoDocumento).where(
        PagoDocumento.cliente_id == client.id,
        PagoDocumento.documento_uuid.in_([r.uuid for r in invoices if r.metodo_pago == 'PPD'])))}
    unpaid = [r for r in invoices if r.tipo == 'I' and r.metodo_pago == 'PPD' and r.uuid not in paid]
    return by_date + payments, unpaid

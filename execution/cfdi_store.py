"""Persistencia de CFDI por cliente: guardar lo leído de los ZIP y consultar por periodo."""
from typing import Iterable

from sqlalchemy import select, and_, or_
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

    session.commit()
    return stats


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

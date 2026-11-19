"""Complementos de pago (REP) y DIOT con base de flujo de efectivo."""
from datetime import datetime
from decimal import Decimal as D

import pytest

from app.workers.database import database_worker
from execution import cfdi_store, diot
from execution.month_process import process_folder
from execution.xml_file import XmlFile
from models import Cliente
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC
from tests.cfdi_builder import Cfdi, Concepto, Pago, DoctoPagado

ENERO, FEBRERO = datetime(2025, 1, 10), datetime(2025, 2, 5)


@pytest.fixture
def cliente_db():
    with database_worker.new_session() as session:
        client = Cliente(rfc=CLIENTE_RFC, nombre='C', apellido_paterno='', apellido_materno='')
        session.add(client)
        session.commit()
        return client


def factura(importe, metodo='PPD', fecha=ENERO, **kw):
    return Cfdi(emisor_rfc=PROVEEDOR_RFC, emisor_nombre='Proveedor', receptor_rfc=CLIENTE_RFC, fecha=fecha,
                metodo_pago=metodo, conceptos=[Concepto(importe)], **kw)


def rep(documentos, fecha=FEBRERO, version='2.0', moneda='MXN', tipo_cambio='1'):
    return Cfdi(emisor_rfc=PROVEEDOR_RFC, emisor_nombre='Proveedor', receptor_rfc=CLIENTE_RFC, fecha=fecha,
                tipo='P', conceptos=[Concepto(0, traslados=[])], pagos_version=version,
                pagos=[Pago(fecha, documentos, moneda=moneda, tipo_cambio=tipo_cambio)])


def load(client, tmp_path, name, cfdis):
    for c in cfdis:
        c.write(tmp_path / name)
    process_folder(client, tmp_path / name)


def diot_rows(client, year, month):
    with database_worker.new_session() as session:
        records, unpaid = cfdi_store.cash_records(session, client, year, month)
    return diot.aggregate(records), unpaid


def test_parse_pagos20(xml_dir):
    pago = rep([DoctoPagado('ABC', D('580.00'), {'0.160000': D(500)})])
    (row,) = XmlFile(pago.write(xml_dir)).pagos
    assert (row['documento_uuid'], row['fecha_pago'], row['imp_pagado'], row['con_impuestos']) == \
           ('ABC', FEBRERO, D('580.00'), True)
    assert (row['base_tasa16'], row['iva']) == (D('500.00'), D('80.00'))


def test_parse_pagos_en_dolares(xml_dir):
    # Factura en USD pagada en USD con tipo de cambio 17.50 -> pesos
    pago = rep([DoctoPagado('ABC', D('116.00'), {'0.160000': D(100)}, moneda='USD')],
               moneda='USD', tipo_cambio='17.50')
    (row,) = XmlFile(pago.write(xml_dir)).pagos
    assert (row['imp_pagado'], row['base_tasa16']) == (D('2030.00'), D('1750.00'))


def test_ppd_se_reporta_en_el_mes_del_pago(cliente_db, tmp_path):
    ppd = factura(1000)
    pue = factura(300, metodo='PUE')
    load(cliente_db, tmp_path, 'enero', [ppd, pue])
    (p,), unpaid = diot_rows(cliente_db, 2025, 1)
    assert (p.base16, [r.uuid for r in unpaid]) == (D('300.00'), [ppd.uuid])  # enero: solo la PUE; PPD sin pago

    load(cliente_db, tmp_path, 'febrero', [rep([DoctoPagado(ppd.uuid, D('1160.00'), {'0.160000': D(1000)})])])
    (p,), unpaid = diot_rows(cliente_db, 2025, 1)
    assert (p.base16, unpaid) == (D('300.00'), [])  # ya tiene pago registrado (en febrero)

    (p,), unpaid = diot_rows(cliente_db, 2025, 2)
    assert (p.base16, unpaid) == (D('1000.00'), [])  # febrero: el pago de la PPD


def test_pagos10_se_prorratea_con_la_factura(cliente_db, tmp_path):
    ppd = factura(1000)
    load(cliente_db, tmp_path, 'enero', [ppd])
    load(cliente_db, tmp_path, 'febrero', [rep([DoctoPagado(ppd.uuid, D('580.00'))], version='1.0')])

    (p,), _ = diot_rows(cliente_db, 2025, 2)
    assert p.base16 == D('500.00')  # mitad pagada
    assert p.warnings == []
    assert diot.line_2025(p)[21] == '80'


def test_pago_sin_factura_ni_desglose_asume_16_y_avisa(cliente_db, tmp_path):
    load(cliente_db, tmp_path, 'febrero', [rep([DoctoPagado('NO-EXISTE', D('1160.00'))], version='1.0')])
    (p,), _ = diot_rows(cliente_db, 2025, 2)
    assert p.base16 == D('1000')
    assert p.warnings and 'IVA 16' in p.warnings[0]


def test_pago_cancelado_no_cuenta(cliente_db, tmp_path):
    ppd = factura(1000)
    pago = rep([DoctoPagado(ppd.uuid, D('1160.00'), {'0.160000': D(1000)})])
    load(cliente_db, tmp_path, 'enero', [ppd])
    load(cliente_db, tmp_path, 'febrero', [pago])
    with database_worker.new_session() as session:
        cfdi_store.set_cancelled(session, cliente_db, pago.uuid)
    providers, _ = diot_rows(cliente_db, 2025, 2)
    assert providers == []


def test_reimportar_pago_no_duplica(cliente_db, tmp_path):
    ppd = factura(1000)
    pago = rep([DoctoPagado(ppd.uuid, D('580.00'), {'0.160000': D(500)})])
    load(cliente_db, tmp_path, 'enero', [ppd])
    load(cliente_db, tmp_path, 'febrero', [pago])
    load(cliente_db, tmp_path, 'febrero2', [pago])
    (p,), _ = diot_rows(cliente_db, 2025, 2)
    assert (p.base16, p.documentos) == (D('500.00'), 1)


def test_zip_con_facturas_y_rep_de_otro_mes(cliente_db, tmp_path):
    # Un REP de febrero dentro del ZIP de compras de enero no debe rechazarse por "varios meses"
    ppd = factura(1000)
    load(cliente_db, tmp_path, 'mixto', [factura(200, metodo='PUE'), ppd,
                                        rep([DoctoPagado(ppd.uuid, D('1160.00'), {'0.160000': D(1000)})])])
    (p,), _ = diot_rows(cliente_db, 2025, 2)
    assert p.base16 == D('1000.00')

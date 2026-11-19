from calendar import month_name
from datetime import datetime
from decimal import Decimal as D

import pytest
from openpyxl import load_workbook

from app.workers.database import database_worker
from execution import cfdi_store
from execution.month_process import process_folder
from models import Cliente, Comprobante
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC, CASES_BY_ID
from tests.cfdi_builder import Cfdi, Concepto

ENERO = datetime(2025, 1, 10, 9, 0, 0)


@pytest.fixture
def cliente_db():
    with database_worker.new_session() as session:
        client = Cliente(rfc=CLIENTE_RFC, nombre='CLIENTE', apellido_paterno='DE', apellido_materno='PRUEBA')
        session.add(client)
        session.commit()
        return client


def venta(importe, uuid=None):
    kw = {'uuid': uuid} if uuid else {}
    return Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc=PROVEEDOR_RFC, fecha=ENERO, conceptos=[Concepto(importe)], **kw)


def zip_folder(tmp_path, name, cfdis):
    folder = tmp_path / name
    for c in cfdis:
        c.write(folder)
    return folder


def sheet_totals(result):
    sheet = load_workbook(result.summary.filename)[month_name[1].capitalize()]
    return sorted(sheet.cell(r, 4).value for r in range(6, sheet.max_row + 1)
                  if isinstance(sheet.cell(r, 1).value, datetime))


def test_varios_zip_del_mismo_mes_se_acumulan_sin_duplicar(cliente_db, tmp_path):
    repetida = venta(100)
    r1 = process_folder(cliente_db, zip_folder(tmp_path, 'a', [repetida, venta(200)]), origen='a.zip')
    assert (r1.nuevos, r1.actualizados, r1.total_mes) == (2, 0, 2)

    r2 = process_folder(cliente_db, zip_folder(tmp_path, 'b', [repetida, venta(300)]), origen='b.zip')
    assert (r2.nuevos, r2.actualizados, r2.total_mes) == (1, 1, 3)
    assert sheet_totals(r2) == [100, 200, 300]


def test_cancelados_se_excluyen_y_se_conservan_al_reimportar(cliente_db, tmp_path):
    cancelada = venta(500)
    folder = zip_folder(tmp_path, 'a', [cancelada, venta(100)])
    process_folder(cliente_db, folder)

    with database_worker.new_session() as session:
        assert cfdi_store.set_cancelled(session, cliente_db, cancelada.uuid)

    result = process_folder(cliente_db, folder)  # reimportar no debe quitar la marca
    assert sheet_totals(result) == [100]


def test_importes_exactos_en_bd(cliente_db, tmp_path):
    case = CASES_BY_ID['v40_honorarios_retenciones']
    cfdi = Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc=PROVEEDOR_RFC, fecha=ENERO,
                conceptos=case.cfdi.conceptos)
    process_folder(cliente_db, zip_folder(tmp_path, 'a', [cfdi]))
    with database_worker.new_session() as session:
        (record,) = session.query(Comprobante).all()
    assert (record.total, record.ret_iva, record.ret_isr, record.gravado) == (
        D('9533.33'), D('1066.67'), D('1000.00'), D('10000.00'))
    assert isinstance(record.total, D)


def test_proveedores_desde_bd(cliente_db, tmp_path):
    result = process_folder(cliente_db, zip_folder(tmp_path, 'a', [venta(100), venta(50)]), create_providers=True)
    assert result.providers.filename.exists()
    txt = next((result.providers.filename.parent / 'proveedores').glob('*.txt'))
    assert len(txt.read_text().splitlines()) == 1  # un proveedor, una sola línea


def test_carpeta_sin_xml(cliente_db, tmp_path):
    from exceptions import ValidationException
    (tmp_path / 'vacio').mkdir()
    with pytest.raises(ValidationException):
        process_folder(cliente_db, tmp_path / 'vacio')

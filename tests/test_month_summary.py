from calendar import month_name
from datetime import datetime
from decimal import Decimal as D

import pytest
from openpyxl import load_workbook

from exceptions import ValidationException
from execution.month_summary import MonthSummary
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC, CASES_BY_ID
from tests.cfdi_builder import Cfdi, Concepto

ENERO = datetime(2025, 1, 10, 9, 0, 0)


def emitida(importe, tipo='I', fecha=ENERO, **kw):
    return Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc=PROVEEDOR_RFC, receptor_nombre='Proveedor Uno',
                fecha=fecha, tipo=tipo, conceptos=[Concepto(importe)], **kw)


def generate(cliente, xml_dir, cfdis):
    for c in cfdis:
        c.write(xml_dir)
    summary = MonthSummary(cliente)
    summary.add_files_in_folder(xml_dir)
    summary.save()
    return summary


def rows(sheet, first=6):
    """Filas de datos (fecha en col A) como tuplas de valores desde la columna D."""
    out = []
    for r in range(first, sheet.max_row + 1):
        if isinstance(sheet.cell(r, 1).value, datetime):
            out.append(tuple(sheet.cell(r, c).value for c in range(4, sheet.max_column + 1)))
    return out


def test_writes_only_inside_isolated_workdir(cliente, xml_dir, workdir):
    summary = generate(cliente, xml_dir, [emitida(100)])
    assert summary.filename.is_relative_to(workdir)
    assert summary.filename.exists()


def test_ingresos_iva_nota_credito_y_totales(cliente, xml_dir):
    summary = generate(cliente, xml_dir, [emitida(100), emitida(200), emitida(50, tipo='E')])

    assert summary.rev is True
    assert summary.filename.name == f'{CLIENTE_RFC} 2025 INGRESOS.xlsx'

    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    assert [sheet.cell(4, c).value for c in (4, 5, 6)] == ['SUBTOTAL', 'IVA', 'TOTAL']
    assert sorted(rows(sheet)) == sorted([(100, 16, 116), (200, 32, 232), (-50, -8, -58)])
    assert sheet.cell(2, 1).value == 'CONCENTRADO DE INGRESOS'
    assert sheet.cell(6, 2).value == 'PROVEEDOR UNO'

    # Lo que lee el concentrado anual
    reread = MonthSummary(cliente, year=2025, month=1, rev=True)
    assert (reread.subtotal, reread.iva, reread.ieps) == (D('250.00'), D('40.00'), D('0.00'))


def test_egresos_cuando_cliente_es_receptor(cliente, xml_dir):
    recibida = Cfdi(emisor_rfc=PROVEEDOR_RFC, receptor_rfc=CLIENTE_RFC, fecha=ENERO, conceptos=[Concepto(300)])
    summary = generate(cliente, xml_dir, [recibida])
    assert summary.rev is False
    assert summary.filename.name == f'{CLIENTE_RFC} 2025 EGRESOS.xlsx'


def test_pago_en_cero_y_nomina_omitida(cliente, xml_dir):
    pago = CASES_BY_ID['v40_pago'].cfdi
    nomina = CASES_BY_ID['v40_nomina'].cfdi
    summary = generate(cliente, xml_dir, [emitida(100), pago, nomina])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    assert sorted(rows(sheet)) == sorted([(100, 16, 116), (0, 0, 0)])


def test_columnas_con_retenciones(cliente, xml_dir):
    case = CASES_BY_ID['v40_honorarios_retenciones']
    summary = generate(cliente, xml_dir, [case.cfdi])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    headers = [sheet.cell(4, c).value for c in range(4, sheet.max_column + 1)]
    assert headers == ['SUBTOTAL', 'IVA', 'TOTAL', 'RET IVA', 'RET ISR', 'NETO']


def test_rechaza_xml_de_otro_cliente(cliente, xml_dir):
    ajena = Cfdi(emisor_rfc=PROVEEDOR_RFC, receptor_rfc='ZZZ010101ZZZ', fecha=ENERO, conceptos=[Concepto(10)])
    with pytest.raises(ValidationException):
        generate(cliente, xml_dir, [ajena])


def test_zip_con_varios_meses_no_se_mezcla(cliente, xml_dir):
    febrero = datetime(2025, 2, 3, 9, 0, 0)
    with pytest.raises(ValidationException):
        generate(cliente, xml_dir, [emitida(100), emitida(200, fecha=febrero)])


def test_nota_credito_con_retenciones_resta(cliente, xml_dir):
    from tests.cfdi_builder import Retencion, ISR
    nc = Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc=PROVEEDOR_RFC, fecha=ENERO, tipo='E',
              conceptos=[Concepto(1000, retenciones=[Retencion(ISR, '0.100000')])])
    summary = generate(cliente, xml_dir, [nc])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    (row,) = rows(sheet)
    # SUBTOTAL, IVA, TOTAL, RET IVA, RET ISR, NETO -> todo negativo
    assert row == (-1000, -160, -1160, 0, -100, -1060)


def test_ieps_gravado_desde_conceptos(cliente, xml_dir):
    summary = generate(cliente, xml_dir, [CASES_BY_ID['v40_ieps_iva'].cfdi])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    assert [sheet.cell(4, c).value for c in range(4, 9)] == ['NO GRAVADO', 'GRAVADO', 'IEPS', 'IVA', 'TOTAL']
    assert rows(sheet) == [(200, 500, 40, 86.4, 826.4)]


def test_ieps_con_retenciones(cliente, xml_dir):
    summary = generate(cliente, xml_dir, [CASES_BY_ID['v40_ieps_y_retenciones'].cfdi])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    # NO GRAVADO, GRAVADO, IEPS, IVA, TOTAL, RET IVA, RET ISR, NETO
    assert rows(sheet) == [(0, 1000, 80, 172.8, 1252.8, 0, 12.5, 1240.3)]


def test_usd_en_pesos(cliente, xml_dir):
    summary = generate(cliente, xml_dir, [CASES_BY_ID['v40_usd'].cfdi])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    assert rows(sheet) == [(1750, 280, 2030)]


def test_publico_en_general(cliente, xml_dir):
    venta = Cfdi(emisor_rfc=CLIENTE_RFC, receptor_rfc='XAXX010101000', receptor_nombre='Juan Perez',
                 fecha=ENERO, conceptos=[Concepto(100)])
    summary = generate(cliente, xml_dir, [venta])
    sheet = load_workbook(summary.filename)[month_name[1].capitalize()]
    assert sheet.cell(6, 2).value == 'PUBLICO EN GENERAL'


def test_rechaza_emitidas_y_recibidas_juntas(cliente, xml_dir):
    recibida = Cfdi(emisor_rfc=PROVEEDOR_RFC, receptor_rfc=CLIENTE_RFC, fecha=ENERO, conceptos=[Concepto(300)])
    with pytest.raises(ValidationException):
        generate(cliente, xml_dir, [emitida(100), recibida])

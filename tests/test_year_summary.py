from calendar import month_name
from datetime import datetime
from decimal import Decimal as D

import pytest
from openpyxl import Workbook, load_workbook

from execution.month_summary import MonthSummary
from execution.year_summary import YearSummary
from tests.cases import CLIENTE_RFC, PROVEEDOR_RFC
from tests.cfdi_builder import Cfdi, Concepto

YEAR = 2025


def month_file(cliente, folder, month, ingresos=(), egresos=()):
    """Genera los concentrados mensuales de ingresos y egresos con un CFDI por importe."""
    fecha = datetime(YEAR, month, 10, 9, 0, 0)
    for kind, importes in (('ing', ingresos), ('egr', egresos)):
        if not importes: continue
        sub = folder / f'{month}-{kind}'
        for importe in importes:
            emisor, receptor = (CLIENTE_RFC, PROVEEDOR_RFC) if kind == 'ing' else (PROVEEDOR_RFC, CLIENTE_RFC)
            Cfdi(emisor_rfc=emisor, receptor_rfc=receptor, fecha=fecha, conceptos=[Concepto(importe)]).write(sub)
        summary = MonthSummary(cliente)
        summary.add_files_in_folder(sub)
        summary.save()


def iva_block(sheet):
    """B22..B26: causado, acreditable, diferencia, saldo anterior, a cargo o favor."""
    return [sheet.cell(r, 2).value for r in range(22, 27)]


def year_sheet(cliente, month):
    summary = YearSummary(cliente, YEAR)
    summary.generate_sheet(month)
    summary.save()
    return load_workbook(summary.filename), month_name[month].capitalize()


def test_get_prev_data_from_sheet():
    sheet = Workbook().active
    sheet.cell(row=12, column=5).value = D('100.10')
    sheet.cell(row=19, column=5).value = D('50.05')
    sheet.cell(row=40, column=1).value = 'IVA A CARGO O FAVOR'
    sheet.cell(row=40, column=2).value = D('12.34')
    assert YearSummary.get_prev_data_from_sheet(sheet) == (D('100.10'), D('50.05'), D('12.34'))


def test_un_mes_a_cargo(cliente, xml_dir):
    month_file(cliente, xml_dir, 1, ingresos=[1000], egresos=[500])
    wb, enero = year_sheet(cliente, 1)
    sheet = wb[enero]

    assert sheet.cell(6, 2).value == 1000  # ingresos del mes
    assert sheet.cell(7, 2).value == 500  # egresos del mes
    assert iva_block(sheet) == [160, 80, 80, 0, 80]


def test_saldo_a_favor_se_acumula(cliente, xml_dir):
    # Convención propuesta: positivo = a cargo, negativo = a favor (a validar con la contadora)
    month_file(cliente, xml_dir, 1, ingresos=[100], egresos=[300])  # IVA 16 - 48 = -32 (a favor)
    month_file(cliente, xml_dir, 2, ingresos=[100], egresos=[200])  # IVA 16 - 32 = -16 (a favor)
    wb, febrero = year_sheet(cliente, 2)

    assert iva_block(wb[month_name[1].capitalize()])[-1] == -32
    assert iva_block(wb[febrero]) == [16, 32, -16, -32, -48]


def test_regenerar_no_duplica_hojas(cliente, xml_dir):
    month_file(cliente, xml_dir, 1, ingresos=[100], egresos=[50])
    for _ in range(2):
        summary = YearSummary(cliente, YEAR)
        summary.generate_sheet(1, replace=True)
        summary.save()
    assert load_workbook(summary.filename).sheetnames == [month_name[1].capitalize()]


def test_regenerar_abril_no_duplica_hojas_ni_pago(cliente, xml_dir):
    for month in range(1, 5):
        month_file(cliente, xml_dir, month, ingresos=[100 * month], egresos=[50])
    for _ in range(2):
        summary = YearSummary(cliente, YEAR)
        summary.generate_sheet(4, replace=True)
        summary.save()

    names = [month_name[m].capitalize() for m in range(1, 5)]
    wb = load_workbook(summary.filename)
    assert sorted(wb.sheetnames) == sorted(names + [f'{names[3]} pago'])

    # La hoja de pago acumula los ingresos de marzo (300) con los de abril (400)
    pago = wb[f'{names[3]} pago']
    assert pago.cell(6, 2).value == 400
    assert pago.cell(11, 5).value == 300


def test_saldo_a_cargo_no_se_arrastra(cliente, xml_dir):
    month_file(cliente, xml_dir, 1, ingresos=[1000], egresos=[500])  # 160 - 80 = 80 a cargo (se paga)
    month_file(cliente, xml_dir, 2, ingresos=[100], egresos=[300])   # 16 - 48 = -32 a favor
    wb, febrero = year_sheet(cliente, 2)
    assert iva_block(wb[febrero]) == [16, 48, -32, 0, -32]
    assert wb[febrero].cell(26, 4).value == 'A FAVOR'


def test_saldo_a_favor_se_compensa(cliente, xml_dir):
    month_file(cliente, xml_dir, 1, ingresos=[100], egresos=[300])   # -32 a favor
    month_file(cliente, xml_dir, 2, ingresos=[1000], egresos=[500])  # 80 a cargo - 32 = 48
    wb, febrero = year_sheet(cliente, 2)
    assert iva_block(wb[febrero]) == [160, 80, 80, -32, 48]
    assert wb[febrero].cell(26, 4).value == 'A CARGO'


def test_pago_bimestral_suma_saldo_completo(cliente, xml_dir):
    month_file(cliente, xml_dir, 1, ingresos=[100], egresos=[100])   # 0
    month_file(cliente, xml_dir, 2, ingresos=[100], egresos=[100])   # 0
    month_file(cliente, xml_dir, 3, ingresos=[1000], egresos=[500])  # +80 a cargo
    month_file(cliente, xml_dir, 4, ingresos=[1000], egresos=[500])  # +80 a cargo
    wb, abril = year_sheet(cliente, 4)
    assert iva_block(wb[abril])[-1] == 80            # mensual: marzo a cargo no se arrastra
    assert iva_block(wb[f'{abril} pago'])[-1] == 160  # bimestral: marzo + abril

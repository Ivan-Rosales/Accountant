from datetime import datetime
from decimal import Decimal as D

from openpyxl import Workbook, load_workbook

from app.workers.import_files import ImportFilesWorker
from execution.month_summary import MonthSummary
from tests.cases import CLIENTE_RFC


def legacy_month_file(folder, headers, data_rows, kind='EGRESOS'):
    """Archivo mensual con el formato del programa anterior (Tkinter)."""
    wb = Workbook()
    sheet = wb.active
    sheet.title = '1'
    sheet.cell(2, 1).value = f'CONCENTRADO DE {kind}'
    for col, header in enumerate(headers, 4):
        sheet.cell(4, col).value = header
    for r, (fecha, nombre, folio, *values) in enumerate(data_rows, 6):
        sheet.cell(r, 1).value = fecha
        sheet.cell(r, 2).value = nombre
        sheet.cell(r, 3).value = folio
        for col, value in enumerate(values, 4):
            sheet.cell(r, col).value = value
    path = folder / f'2025 {CLIENTE_RFC} {kind} 1.xlsx'
    wb.save(path)
    return path


def test_importa_retenciones_con_doble_espacio(cliente, tmp_path):
    headers = ['SUBTOTAL', 'IVA', 'TOTAL', 'RET  IVA', 'RET  ISR', 'NETO']
    fecha = datetime(2025, 1, 10)
    path = legacy_month_file(tmp_path, headers, [
        (fecha, 'HONORARIOS', 'F/1', 10000, 1600, 11600, 1066.67, 1000, 9533.33),
    ])
    worker = ImportFilesWorker()
    worker.client = cliente
    worker.generate_month_file(path)

    reread = MonthSummary(cliente, year=2025, month=1, rev=False)
    sheet = load_workbook(reread.filename).worksheets[0]
    headers_new = [sheet.cell(4, c).value for c in range(4, sheet.max_column + 1)]
    assert headers_new == ['SUBTOTAL', 'IVA', 'TOTAL', 'RET IVA', 'RET ISR', 'NETO']
    assert [sheet.cell(6, c).value for c in range(4, 10)] == [10000, 1600, 11600, 1066.67, 1000, 9533.33]


def test_saldo_importado_con_signo():
    from openpyxl import Workbook
    worker = ImportFilesWorker()
    worker.workbook = Workbook()
    sheet = worker.workbook.active
    sheet.title = '1'
    sheet.cell(6, 5).value = 100   # IVA causado
    sheet.cell(7, 5).value = 300   # IVA acreditable
    sheet.cell(25, 2).value = 50   # saldo a favor arrastrado (positivo en el programa anterior)
    for cell in ((11, 5), (6, 2), (18, 5), (7, 2)):
        sheet.cell(*cell).value = 0
    *_, iva = worker.get_prev_data(2)
    assert iva == D('-250.00')  # a favor

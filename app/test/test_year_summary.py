import random
import unittest
from datetime import datetime
from decimal import Decimal

from openpyxl import Workbook

from app.workers.database import database_worker
from execution.year_summary import YearSummary
from models import Cliente


class YearSummaryTest(unittest.TestCase):
    def test_generate_year_summary(self):
        data = database_worker.session.query(Cliente).all()
        now = datetime.now()
        client = data[0]

        summary = YearSummary(client, now.year)
        summary.generate_sheet(12)
        summary.save()

    def test_get_prev_data(self):
        workbook = Workbook()
        sheet = workbook.active

        total_ingresos = Decimal(random.uniform(1, 1000))
        total_egresos = Decimal(random.uniform(1, 1000))
        total_iva = Decimal(random.uniform(1, 1000))

        sheet.cell(row=12, column=5).value = total_ingresos
        sheet.cell(row=19, column=5).value = total_egresos

        row = random.randint(10, 100)
        sheet.cell(row=row, column=1).value = 'IVA A CARGO O FAVOR'
        sheet.cell(row=row, column=2).value = total_iva

        results = YearSummary.get_prev_data_from_sheet(sheet)

        self.assertEqual(total_ingresos, results[0], 'ingresos is wrong')
        self.assertEqual(total_egresos, results[1], 'egresos is wrong')
        self.assertEqual(total_iva, results[2], 'iva is wrong')

import unittest
from datetime import datetime

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

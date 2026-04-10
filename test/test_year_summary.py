import random
import unittest

from app.workers.database import SessionLocal
from execution.year_summary import YearSummary
from models import Cliente


class YearSummaryTest(unittest.TestCase):
    def test_generate_providers_file(self):
        session = SessionLocal()
        data = session.query(Cliente).all()
        client = random.choice(data)

        summary = YearSummary(client, 2024)
        summary.generate_sheet(4)
        summary.save()


if __name__ == '__main__':
    unittest.main()

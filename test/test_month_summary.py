import random
import unittest

from app.workers.database import SessionLocal
from core.faker import XmlFileFaker
from models import Cliente
from worker.month_summary import MonthSummary
from worker.xml_file import XmlFile


class MonthSummaryTest(unittest.TestCase):
    def test_generate_providers_file(self):
        session = SessionLocal()
        data = session.query(Cliente).all()
        client = random.choice(data)

        generator = XmlFileFaker(client)
        file = XmlFile(generator())
        summary = MonthSummary(client)
        summary.add_file(file)

        summary.client.rfc = ''
        summary.generate_providers()


if __name__ == '__main__':
    unittest.main()

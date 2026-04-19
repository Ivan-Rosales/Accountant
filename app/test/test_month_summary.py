import random
import shutil
import unittest
from datetime import datetime

from app.test.core.faker import XmlFileFaker
from app.workers.database import database_worker
from execution.month_summary import MonthSummary
from execution.month_summary_providers import MonthSummaryProviders
from execution.xml_file import XmlFile
from models import Cliente


class MonthSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clients = database_worker.session.query(Cliente).all()
        cls.client = cls.clients[0]

        shutil.rmtree(MonthSummary(cls.client).filename.parent)

    def test_generate_file_year(self):
        for i in range(1, 13):
            self.test_generate_file(month=i)
            self.test_generate_file(month=i, invert=True)

        self.test_generate_providers_file(month=1)

    def test_generate_file(self, **kwargs):
        invert = kwargs.pop('invert', False)
        date = datetime.now().replace(**kwargs)

        summary = MonthSummary(self.client)

        for i in range(5):
            params = [self.client, random.choice(self.clients)]
            if invert: params.reverse()

            generator = XmlFileFaker(*params, date=date)
            file = XmlFile(generator())
            summary.add_file(file)

        summary.save()

    def test_generate_providers_file(self, **kwargs):
        date = datetime.now().replace(**kwargs)

        summary = MonthSummaryProviders(self.client)

        for i in range(3):
            provider = random.choice(self.clients)

            for j in range(5):
                generator = XmlFileFaker(self.client, provider, date=date)
                file = XmlFile(generator())
                summary.add_file(file)

        summary.save()

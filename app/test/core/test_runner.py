import unittest

from app.test.test_month_summary import MonthSummaryTest
from app.test.test_year_summary import YearSummaryTest


def start_test():
    suite = unittest.TestSuite()
    suite.addTest(MonthSummaryTest('test_generate_file_year'))
    suite.addTest(YearSummaryTest('test_generate_year_summary'))
    runner = unittest.TextTestRunner()
    runner.run(suite)

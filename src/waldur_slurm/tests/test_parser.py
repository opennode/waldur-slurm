from django.test import TestCase

from waldur_slurm.parser import UsageReportParser


VALID_ALLOCATION = 'allocation1'

VALID_REPORT = """
allocation1|cpu=1,mem=51200M,node=1,gres/gpu=1,gres/gpu:tesla=1|00:01:00|user1|
allocation1|cpu=2,mem=51200M,node=2,gres/gpu=2,gres/gpu:tesla=1|00:02:00|user2|
"""


class ParserTest(TestCase):
    def setUp(self):
        parser = UsageReportParser(VALID_REPORT)
        self.report = parser.get_report()

    def test_usage_contains_report_for_each_account(self):
        self.assertTrue(VALID_ALLOCATION in self.report)

    def test_usage_contains_report_for_total_usage(self):
        self.assertTrue('TOTAL_ACCOUNT_USAGE' in self.report[VALID_ALLOCATION])

    def test_total_cpu_is_calculated_correctly(self):
        total = self.report[VALID_ALLOCATION]['TOTAL_ACCOUNT_USAGE']
        expected = 1 + 2 * 2 * 2
        self.assertEqual(total.cpu, expected)

    def test_total_gpu_is_calculated_correctly(self):
        total = self.report[VALID_ALLOCATION]['TOTAL_ACCOUNT_USAGE']
        expected = 1 + 2 * 2 * 2
        self.assertEqual(total.gpu, expected)

    def test_total_ram_is_calculated_correctly(self):
        total = self.report[VALID_ALLOCATION]['TOTAL_ACCOUNT_USAGE']
        expected = (1 + 2 * 2) * 51200 * 2**20
        self.assertEqual(total.ram, expected)

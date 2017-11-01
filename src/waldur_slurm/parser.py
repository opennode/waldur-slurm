import datetime
import operator
import re

from django.utils.functional import cached_property

from waldur_slurm.structures import Quotas

SLURM_UNIT_PATTERN = re.compile('(\d+)([KMGTP]?)')

SLURM_UNITS = {
    'K': 2**10,
    'M': 2**20,
    'G': 2**30,
    'T': 2**40,
}


def parse_int(value):
    """
    Convert 5K to 5000.
    """
    match = re.match(SLURM_UNIT_PATTERN, value)
    if not match:
        return 0
    value = int(match.group(1))
    unit = match.group(2)
    if unit:
        factor = SLURM_UNITS[unit]
    else:
        factor = 1
    return factor * value


def parse_duration(value):
    """
    Returns duration in minutes as an integer number.
    For example 00:01:00 is equal to 1
    """
    dt = datetime.datetime.strptime(value, '%H:%M:%S')
    delta = datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)
    return int(delta.total_seconds()) // 60


class UsageLineParser(object):
    def __init__(self, line):
        self._parts = line.split('|')

    # Public part

    @cached_property
    def account(self):
        return self._parts[0]

    @cached_property
    def user(self):
        return self._parts[3]

    @cached_property
    def quotas(self):
        return Quotas(self.cpu_norm, self.gpu_norm, self.ram_norm)

    # Private part

    @cached_property
    def cpu_norm(self):
        return self.cpu * self.elapsed * self.node

    @cached_property
    def gpu_norm(self):
        return self.gpu * self.elapsed * self.node

    @cached_property
    def ram_norm(self):
        return self.ram * self.elapsed * self.node

    @cached_property
    def cpu(self):
        return self.parse_field('cpu')

    @cached_property
    def gpu(self):
        return self.parse_field('gres/gpu')

    @cached_property
    def ram(self):
        return self.parse_field('mem')

    @cached_property
    def node(self):
        return self.parse_field('node')

    @cached_property
    def elapsed(self):
        return parse_duration(self._parts[2])

    @cached_property
    def _resources(self):
        pairs = self._parts[1].split(',')
        return dict(pair.split('=') for pair in pairs)

    def parse_field(self, field):
        return parse_int(self._resources[field])


class UsageReportParser(object):
    def __init__(self, data):
        self.lines = [line for line in data.splitlines() if '|' in line]
        self.report = {}

    # Public part

    def get_report(self):
        for line in self.lines:
            self.add_line(UsageLineParser(line))

        self.calculate_total_usage()

        return self.report

    # Private part

    def add_line(self, report_line):
        account = report_line.account
        user = report_line.user
        quotas = report_line.quotas

        self.report.setdefault(account, {}).setdefault(user, Quotas(0, 0, 0))
        self.report[account][user] += quotas

    def calculate_total_usage(self):
        for usage in self.report.values():
            quotas = usage.values()
            total = reduce(operator.add, quotas)
            usage['TOTAL_ACCOUNT_USAGE'] = total

from __future__ import division

import decimal

from django.utils.functional import cached_property

from waldur_slurm.structures import Quotas


class UsageLineParser(object):
    def __init__(self, line):
        self._parts = line.split('|')

    def get_int(self, index):
        value = self._parts[index] or 0
        return int(value)

    @cached_property
    def cpu(self):
        return self.get_int(1)

    @cached_property
    def gpu(self):
        return self.get_int(2)

    @cached_property
    def ram(self):
        return self.get_int(3)

    @cached_property
    def duration(self):
        duration = self.get_int(4)
        # convert from seconds to minutes
        return duration / 60

    @cached_property
    def user(self):
        return self.get_int(5)

    @cached_property
    def charge(self):
        return decimal.Decimal(self._parts[6])

    @cached_property
    def cpu_norm(self):
        return int(round(self.cpu * self.duration))

    @cached_property
    def gpu_norm(self):
        return int(round(self.gpu * self.duration))

    @cached_property
    def ram_norm(self):
        return int(round(self.ram * self.duration))


class UsageReportParser(object):
    def __init__(self, data):
        self.lines = [line for line in data.splitlines() if '|' in line]
        self.report = {}

    def get_quotas(self):
        quotas = Quotas()

        for line in self.lines:
            line_parser = UsageLineParser(line)
            quotas += Quotas(line_parser.cpu_norm,
                             line_parser.gpu_norm,
                             line_parser.ram_norm,
                             line_parser.charge)

        return quotas

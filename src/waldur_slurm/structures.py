import collections

from waldur_slurm.base import BatchError

Account = collections.namedtuple('Account', ['name', 'description', 'organization', 'users'])
Account.__new__.__defaults__ = (None,)
Association = collections.namedtuple('Association', ['account', 'user', 'value'])


class Quotas(object):
    def __init__(self, cpu=None, gpu=None, ram=None, deposit=None):
        self.cpu = cpu
        self.gpu = gpu
        self.ram = ram
        self.deposit = deposit

    def __add__(self, other):
        kwargs = {}

        for limit in ['cpu', 'gpu', 'ram', 'deposit']:
            self_limit = getattr(self, limit)
            other_limit = getattr(other, limit)

            if other_limit is None:
                continue

            if self_limit is None:
                self_limit = 0

            kwargs[limit] = self_limit + other_limit

        return Quotas(**kwargs)

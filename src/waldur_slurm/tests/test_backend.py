from __future__ import unicode_literals

from django.test import TestCase
import mock
from freezegun import freeze_time

from waldur_freeipa import models as freeipa_models
from .. import models
from . import fixtures

VALID_REPORT = """
allocation1|cpu=1,mem=51200M,node=1,gres/gpu=1,gres/gpu:tesla=1|00:01:00|user1|
allocation1|cpu=2,mem=51200M,node=2,gres/gpu=2,gres/gpu:tesla=1|00:02:00|user2|
"""


class BackendTest(TestCase):
    def setUp(self):
        self.fixture = fixtures.SlurmFixture()
        self.allocation = self.fixture.allocation
        self.account = 'waldur_allocation_' + self.allocation.uuid.hex

    @mock.patch('subprocess.check_output')
    def test_usage_synchronization(self, check_output):
        check_output.return_value = VALID_REPORT.replace('allocation1', self.account)

        backend = self.allocation.get_backend()
        backend.sync_usage()
        self.allocation.refresh_from_db()

        self.assertEqual(self.allocation.cpu_usage, 1 + 2 * 2 * 2)
        self.assertEqual(self.allocation.gpu_usage, 1 + 2 * 2 * 2)
        self.assertEqual(self.allocation.ram_usage, (1 + 2 * 2) * 51200 * 2**20)

    @freeze_time('2017-10-16 00:00:00')
    @mock.patch('subprocess.check_output')
    def test_usage_per_user(self, check_output):
        check_output.return_value = VALID_REPORT.replace('allocation1', self.account)

        user1 = self.fixture.manager
        user2 = self.fixture.admin

        freeipa_models.Profile.objects.create(user=user1, username='user1')
        freeipa_models.Profile.objects.create(user=user2, username='user2')

        backend = self.allocation.get_backend()
        backend.sync_usage()

        user1_allocation = models.AllocationUsage.objects.get(
            allocation=self.allocation,
            user=user1,
            year=2017,
            month=10,
        )
        self.assertEqual(user1_allocation.cpu_usage, 1)
        self.assertEqual(user1_allocation.gpu_usage, 1)
        self.assertEqual(user1_allocation.ram_usage, 51200 * 2**20)

    @mock.patch('subprocess.check_output')
    def test_set_resource_limits(self, check_output):
        self.allocation.cpu_limit = 1000
        self.allocation.gpu_limit = 2000
        self.allocation.ram_limit = 3000
        self.allocation.save()

        template = 'sacctmgr --parsable2 --noheader --immediate' \
                   ' modify account %s set GrpTRESMins=cpu=%d,gres/gpu=%d,mem=%d'
        context = (self.account, self.allocation.cpu_limit, self.allocation.gpu_limit, self.allocation.ram_limit)
        command = ['ssh', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no',
                   'root@localhost', '-p', '22', '-i', '/etc/waldur/id_rsa', template % context]

        backend = self.allocation.get_backend()
        backend.set_resource_limits(self.allocation)

        check_output.assert_called_once_with(command, stderr=mock.ANY)

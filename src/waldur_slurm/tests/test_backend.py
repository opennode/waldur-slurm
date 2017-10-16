from __future__ import unicode_literals

from django.test import TestCase
import mock
from freezegun import freeze_time

from waldur_freeipa import models as freeipa_models
from .. import models
from . import fixtures


class BackendTest(TestCase):
    def setUp(self):
        self.fixture = fixtures.SlurmFixture()
        self.allocation = self.fixture.allocation
        self.account = 'waldur_allocation_' + self.allocation.uuid.hex

    @mock.patch('subprocess.check_output')
    def test_usage_synchronization(self, check_output):
        usage_report = """cluster|allocation1|||cpu|2052150|
cluster|allocation1|||mem|6413716577|
cluster|allocation1|||gres/gpu|2650|
cluster|allocation2|||cpu|692886|
cluster|allocation2|||mem|2193728333|
cluster|allocation2|||gres/gpu|0|
"""
        check_output.return_value = usage_report.replace('allocation1', self.account)

        backend = self.allocation.get_backend()
        backend.sync_usage()
        self.allocation.refresh_from_db()

        self.assertEqual(self.allocation.cpu_usage, 2052150)
        self.assertEqual(self.allocation.gpu_usage, 2650)
        self.assertEqual(self.allocation.ram_usage, 6413716577)

    @freeze_time('2017-10-16 00:00:00')
    @mock.patch('subprocess.check_output')
    def test_usage_per_user(self, check_output):
        usage_report = """cluster|allocation1|||cpu|2052150|
        cluster|allocation1|||gres/gpu|2650|
        cluster|allocation1|||mem|6413716577|
        cluster|allocation1|user1||cpu|1026075|
        cluster|allocation1|user1||gres/gpu|820860|
        cluster|allocation1|user1||mem|6413000000|
        cluster|allocation1|user2||cpu|1026075|
        cluster|allocation1|user2||mem|716577|
        cluster|allocation1|user2||gres/gpu|205215|
        """
        check_output.return_value = usage_report.replace('allocation1', self.account)

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
        self.assertEqual(user1_allocation.cpu_usage, 1026075)
        self.assertEqual(user1_allocation.gpu_usage, 820860)
        self.assertEqual(user1_allocation.ram_usage, 6413000000)

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

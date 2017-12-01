import logging
import re
import subprocess  # nosec
import six

from django.utils import timezone

from waldur_core.core import utils as core_utils
from waldur_slurm.parser import UsageReportParser
from waldur_slurm.structures import Account, Association


class SlurmError(Exception):
    pass


logger = logging.getLogger(__name__)


class SlurmClient(object):
    def __init__(self, hostname, key_path, username='root', port=22, use_sudo=False):
        self.hostname = hostname
        self.key_path = key_path
        self.username = username
        self.port = port
        self.use_sudo = use_sudo

    def list_accounts(self):
        output = self._execute_command(['list', 'account'])
        return [self._parse_account(line) for line in output.splitlines() if '|' in line]

    def _parse_account(self, line):
        parts = line.split('|')
        return Account(
            name=parts[0],
            description=parts[1],
            organization=parts[2],
        )

    def get_account(self, name):
        output = self._execute_command(['show', 'account', name])
        lines = [line for line in output.splitlines() if '|' in line]
        if len(lines) == 0:
            return None
        return self._parse_account(lines[0])

    def create_account(self, name, description, organization, parent_name=None):
        parts = [
            'add', 'account', name,
            'description="%s"' % description,
            'organization="%s"' % organization,
        ]
        if parent_name:
            parts.append('parent=%s' % parent_name)
        return self._execute_command(parts)

    def delete_all_users_from_account(self, name):
        return self._execute_command(['remove', 'user', 'where', 'account=%s' % name])

    def account_has_users(self, account):
        output = self._execute_command([
            'show', 'association', 'where', 'account=%s' % account
        ])
        items = [self._parse_association(line) for line in output.splitlines() if '|' in line]
        return any(item.user != '' for item in items)

    def delete_account(self, name):
        if self.account_has_users(name):
            self.delete_all_users_from_account(name)

        return self._execute_command(['remove', 'account', 'where', 'name=%s' % name])

    def set_resource_limits(self, account, quotas):
        quota = 'GrpTRESMins=cpu=%d,gres/gpu=%d,mem=%d' % (quotas.cpu, quotas.gpu, quotas.ram)
        return self._execute_command(['modify', 'account', account, 'set', quota])

    def get_association(self, user, account):
        output = self._execute_command([
            'show', 'association', 'where', 'user=%s' % user, 'account=%s' % account
        ])
        lines = [line for line in output.splitlines() if '|' in line]
        if len(lines) == 0:
            return None
        return self._parse_association(lines[0])

    def _parse_association(self, line):
        parts = line.split('|')
        value = parts[9]
        match = re.match(r'cpu=(\d+)', value)
        if match:
            value = int(match.group(1))
        return Association(
            account=parts[1],
            user=parts[2],
            value=value,
        )

    def create_association(self, username, account, default_account):
        return self._execute_command(['add', 'user', username,
                                      'account=%s' % account,
                                      'DefaultAccount=%s' % default_account])

    def delete_association(self, username, account):
        return self._execute_command([
            'remove', 'user', 'where', 'name=%s' % username, 'and', 'account=%s' % account
        ])

    def get_usage_report(self, accounts):
        today = timezone.now()
        month_start = core_utils.month_start(today).strftime('%Y-%m-%d')
        month_end = core_utils.month_end(today).strftime('%Y-%m-%d')
        args = [
            '--noconvert',
            '--truncate',
            '--allocations',
            '--allusers',
            '--starttime=%s' % month_start,
            '--endtime=%s' % month_end,
            '--accounts=%s' % ','.join(accounts),
            '--format=Account,ReqTRES,Elapsed,User',
        ]
        output = self._execute_command(args, 'sacct', immediate=False)
        parser = UsageReportParser(output)
        return parser.get_report()

    def _execute_command(self, command, command_name='sacctmgr', immediate=True):
        server = '%s@%s' % (self.username, self.hostname)
        port = str(self.port)
        account_command = [command_name, '--parsable2', '--noheader']
        if self.use_sudo:
            account_command.insert(0, 'sudo')
        if immediate:
            account_command.append('--immediate')
        account_command.extend(command)
        ssh_command = ['ssh', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no',
                       server, '-p', port, '-i', self.key_path, ' '.join(account_command)]
        try:
            logger.debug('Executing SSH command: %s', ' '.join(ssh_command))
            return subprocess.check_output(ssh_command, stderr=subprocess.STDOUT)  # nosec
        except subprocess.CalledProcessError as e:
            logger.exception('Failed to execute command "%s".', ssh_command)
            six.reraise(SlurmError, e.output)

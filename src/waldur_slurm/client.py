import collections
import logging
import re
import six
import subprocess

from django.utils import timezone

from nodeconductor.core import utils as core_utils


class SlurmError(Exception):
    pass

User = collections.namedtuple('User', ['name', 'default_account', 'admin_level'])

Account = collections.namedtuple('Account', ['name', 'description', 'organization'])

Association = collections.namedtuple('Association', ['account', 'user', 'value'])

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

    def delete_account(self, name):
        return self._execute_command(['remove', 'account', 'where', 'name=%s' % name])

    def set_cpu_limit(self, account, value):
        quota = 'GrpTRESMins=cpu=%s' % int(value)
        return self._execute_command(['modify', 'account', account, 'set', quota])

    def list_associations(self):
        output = self._execute_command(['list', 'association'])
        return [self._parse_association(line) for line in output.splitlines() if '|' in line]

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

    def create_association(self, username, account):
        return self._execute_command(['add', 'user', username, 'account=%s' % account])

    def delete_association(self, username, account):
        return self._execute_command([
            'remove', 'user', 'where', 'name=%s' % username, 'and', 'account=%s' % account
        ])

    def list_users(self):
        output = self._execute_command(['list', 'user'])
        return [self._parse_user(line) for line in output.splitlines() if '|' in line]

    def _parse_user(self, line):
        parts = line.split('|')
        return User(
            name=parts[0],
            default_account=parts[1],
            admin_level=parts[2],
        )

    def create_user(self, username, default_account):
        return self._execute_command([
            'add', 'user', 'name=%s' % username, 'DefaultAccount=%s' % default_account
        ])

    def delete_user(self, username):
        return self._execute_command(['remove', 'user', username])

    def get_usage(self, accounts):
        today = timezone.now()
        month_start = core_utils.month_start(today).strftime('%Y-%m-%d')
        month_end = core_utils.month_end(today).strftime('%Y-%m-%d')
        args = [
            'cluster', 'AccountUtilizationByUser',
            'Start=%s' % month_start,
            'End=%s' % month_end,
            'Accounts=%s' % ','.join(accounts),
        ]
        output = self._execute_command(args, 'sreport', immediate=False)
        accounts = {}
        for line in output.splitlines():
            if '|' not in line:
                continue
            parts = line.split('|')
            account = parts[1]
            user = parts[2]
            usage = parts[4]
            if not user:
                accounts[account] = usage
        return accounts

    def _execute_command(self, command, command_name='sacctmgr', immediate=True):
        server = '%s@%s' % (self.username, self.hostname)
        port = str(self.port)
        account_command = [command_name, '--parsable2', '--noheader']
        if self.use_sudo:
            account_command.insert(0, 'sudo')
        if immediate:
            account_command.append('--immediate')
        account_command.extend(command)
        ssh_command = ['ssh', server, '-p', port, '-i', self.key_path, ' '.join(account_command)]
        try:
            logging.debug('Executing SSH command: %s', ' '.join(ssh_command))
            return subprocess.check_output(ssh_command, stderr=subprocess.STDOUT)  # nosec
        except subprocess.CalledProcessError as e:
            logger.exception('Failed to execute command "%s".', ssh_command)
            six.reraise(SlurmError, e.output)

import logging
import subprocess  # nosec

import six
from django.utils import timezone

from waldur_core.core import utils as core_utils
from waldur_slurm.base import BatchError, BatchClient
from waldur_slurm.parser_moab import UsageReportParser
from waldur_slurm.structures import Account, Association


class MoabError(BatchError):
    pass


logger = logging.getLogger(__name__)


class MoabClient(BatchClient):
    """ Moab Accounting Manager 9.1.1 Administrator Guide
    http://docs.adaptivecomputing.com/9-1-1/MAM/help.htm"""

    def __init__(self, hostname, key_path, username='root', port=22, use_sudo=False):
        self.hostname = hostname
        self.key_path = key_path
        self.username = username
        self.port = port
        self.use_sudo = use_sudo

    def list_accounts(self):
        output = self._execute_command(
            'mam-list-accounts --raw --quiet --show Name,Users,Description,Organization'.split()
        )
        return [self._parse_account(line) for line in output.splitlines() if '|' in line]

    def _parse_account(self, line):
        parts = line.split('|')
        return Account(
            name=parts[0],
            users=parts[1].split(',') if parts[1] else [],
            description=parts[2],
            organization=parts[3],
        )

    def get_account(self, name):
        command = 'mam-list-accounts --raw --quiet --show Name,Users,Description,Organization -a %s' % name
        output = self._execute_command(command.split())
        lines = [line for line in output.splitlines() if '|' in line]
        if len(lines) == 0:
            return None
        return self._parse_account(lines[0])

    def create_account(self, name, description, organization, parent_name=None):
        command = 'mam-create-account -a %(name)s -d "%(description)s" -o %(organization)s' % {
            'name': name,
            'description': description,
            'organization': organization,
        }
        return self._execute_command(command.split())

    def delete_all_users_from_account(self, account):
        users = self.get_account(account).users
        for usr in users:
            self.delete_association(usr, account)

    def delete_account(self, name):
        command = 'mam-delete-account -a %s' % name
        return self._execute_command(command.split())

    def set_resource_limits(self, account, quotas):
        command = 'mam-deposit -a %(account)s -z %(deposit_amount)s --create-fund True' % {
            'account': account,
            'deposit_amount': quotas.deposit
        }
        return self._execute_command(command.split())

    def get_association(self, user, account):
        command = 'mam-list-funds --raw --quiet -u %(user)s -a %(account)s --show Constraints,Balance' % \
                  {'user': user, 'account': account}
        output = self._execute_command(command.split())
        lines = [line for line in output.splitlines() if '|' in line]
        if len(lines) == 0:
            return None
        
        return Association(
            account=account,
            user=user,
            value=lines[0].split('|')[-1],
        )

    def create_association(self, username, account, default_account=None):
        command = 'mam-modify-account --add-user %(username)s -a %(account)s' % {
            'username': username,
            'account': account
        }
        return self._execute_command(command.split())

    def delete_association(self, username, account):
        command = 'mam-modify-account --del-user %(username)s -a %(account)s' % {
            'username': username,
            'account': account
        }
        return self._execute_command(command.split())

    def get_usage_report(self, accounts):
        account_usage = {}

        for account in accounts:
            command = ('mam-list-usagerecords --raw --quiet --show ' 
                       'Account,Processors,GPUs,Memory,Duration,User,Charge,Nodes ' 
                       '-a %(account)s') % {'account': account}
            output = self._execute_command(command.split())
            parser = UsageReportParser(output)
            account_usage[account] = parser.get_quotas()

        return account_usage

    def _execute_command(self, command):
        server = '%s@%s' % (self.username, self.hostname)
        port = str(self.port)
        if self.use_sudo:
            account_command = ['sudo']
        else:
            account_command = []

        account_command.extend(command)
        ssh_command = ['ssh', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no',
                       server, '-p', port, '-i', self.key_path, ' '.join(account_command)]
        try:
            logger.debug('Executing SSH command: %s', ' '.join(ssh_command))
            return subprocess.check_output(ssh_command, stderr=subprocess.STDOUT)  # nosec
        except subprocess.CalledProcessError as e:
            logger.exception('Failed to execute command "%s".', ssh_command)
            six.reraise(BatchError, e.output)

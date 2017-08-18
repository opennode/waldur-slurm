import logging
import subprocess

from django.conf import settings


logger = logging.getLogger(__name__)


class SLURMBackend(object):
    def __init__(self, options=None):
        self.options = options

    def create_customer(self, customer):
        name = self._get_account_name(customer)
        return self._create_account(name, customer.name, name)

    def create_project(self, project):
        name = self._get_account_name(project)
        parent_name = self._get_account_name(project.customer)
        return self._create_account(name, project.name, name, parent_name)

    def create_allocation(self, allocation):
        return self._create_account(
            name=allocation.name,
            description=allocation.name,
            organization=self._get_account_name(allocation.project),
        )

    def delete_customer(self, customer):
        self._delete_account(self._get_account_name(customer))

    def delete_project(self, project):
        self._delete_account(self._get_account_name(project))

    def delete_allocation(self, allocation):
        self._delete_account(allocation)

    def _get_account_name(self, customer):
        return '%s_%s' % (settings.WALDUR_SLURM['ACCOUNT_NAME_PREFIX'], customer.uuid.hex)

    def _set_allocation_quota(self, allocation, value):
        return self._execute_command([
            'modify', 'account', allocation.name,
            'set', 'GrpTRESMins=%s' % value
        ])

    def _create_account(self, name, description, organization, parent_name=None):
        parts = [
            'add', 'account', name,
            'Description="%s"' % description,
            'Organization="%s"' % organization,
        ]
        if parent_name:
            parts.append('parent_name=%s' % parent_name)
        return self._execute_command(parts)

    def _delete_account(self, name):
        return self._execute_command([
            'remove', 'account', 'where', 'name=%s' % name
        ])

    def _list_accounts(self):
        output = self._execute_command(['list', 'account'])
        return [self._parse_account(line) for line in output.splitlines()]

    def _parse_account(self, line):
        parts = line.split('|')
        return {
            'name': parts[0],
            'description': parts[1],
            'organization': parts[2],
        }

    def _execute_command(self, command):
        host = self.options.host
        username = self.options.username or 'root'
        server ='%s@%s' % (username, host)
        port = str(self.options.port or 22)
        account_command = ['sacctmgr', '--immediate', '--parsable2', '--noheader']
        account_command.extend(command)
        ssh_command = ['ssh', server, '-p', port, "'%s'" % ' '.join(account_command)]
        try:
            return subprocess.check_output(ssh_command, stderr=subprocess.STDOUT)  # nosec
        except subprocess.CalledProcessError:
            logger.exception('Failed to execute command "%s".', ssh_command)

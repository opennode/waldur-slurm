import collections
import logging
import subprocess

import six
from django.conf import settings

from nodeconductor.structure import models as structure_models
from nodeconductor.structure import ServiceBackend, ServiceBackendError
from waldur_freeipa import models as freeipa_models

from . import models


class SLURMError(ServiceBackendError):
    pass


logger = logging.getLogger(__name__)

SLURMUser = collections.namedtuple('SLURMUser', ['name'])

SLURMAccount = collections.namedtuple('SLURMAccount', ['name', 'description', 'organization'])

SLURMAssociation = collections.namedtuple('SLURMAssociation', ['account', 'user', 'value'])


class SLURMBackend(ServiceBackend):
    def __init__(self, settings):
        self.settings = settings

    def sync(self):
        if self.get_allocation_queryset().count() == 0:
            logging.debug('Skipping SLURM service synchronization because there are no allocations.')
            return

        self.sync_users()
        self.sync_customers()
        self.sync_projects()
        self.sync_allocations()
        self.sync_associations()

    def sync_users(self):
        slurm_users = set(user.name for user in self.list_users())
        freeipa_users = set(freeipa_models.Profile.objects.all().values_list('username', flat=True))

        new_users = freeipa_users - slurm_users
        for user in new_users:
            self.create_user(user)

        stale_users = slurm_users - freeipa_users
        for user in stale_users:
            self.delete_user(user)

    def list_users(self):
        output = self._execute_command(['list', 'user'])
        return [self._parse_user(line) for line in output.splitlines()]

    def _parse_user(self, line):
        parts = line.split('|')
        return SLURMUser(name=parts[0])

    def create_user(self, username):
        return self._execute_command(['add', 'user', username])

    def delete_user(self, username):
        return self._execute_command(['remove', 'user', username])

    def sync_customers(self):
        slurm_customers = set(self.list_customers())
        waldur_customers_map = {customer.uuid.hex: customer
                                for customer in structure_models.Customer.objects.all()}
        waldur_customers = set(waldur_customers_map.keys())

        new_customers = waldur_customers - slurm_customers
        for customer in new_customers:
            self.create_customer(waldur_customers_map[customer])

        stale_customers = slurm_customers - waldur_customers
        for customer in stale_customers:
            self.delete_customer(customer)

    def list_customers(self):
        customer_prefix = self.get_customer_prefix()
        customers = []
        for account in self._list_accounts():
            parts = account.name.split(customer_prefix)
            if len(parts) != 2:
                continue
            customers.append(parts[1])
        return customers

    def create_customer(self, customer):
        customer_name = self.get_customer_name(customer)
        return self._create_account(customer_name, customer.name, customer_name)

    def delete_customer(self, customer_uuid):
        customer_name = '%s%s' % (self.get_customer_prefix(), customer_uuid)
        self._delete_account(customer_name)

    def get_customer_name(self, customer):
        return '%s%s' % (self.get_customer_prefix(), customer.uuid.hex)

    def get_customer_prefix(self):
        return '%s_customer_' % settings.WALDUR_SLURM['ACCOUNT_NAME_PREFIX']

    def sync_projects(self):
        slurm_projects = set(self.list_projects())
        waldur_projects_map = {project.uuid.hex: project
                               for project in structure_models.Project.objects.all()}
        waldur_projects = set(waldur_projects_map.keys())

        new_projects = waldur_projects - slurm_projects
        for project in new_projects:
            self.create_project(waldur_projects_map[project])

        stale_projects = slurm_projects - waldur_projects
        for project in stale_projects:
            self.delete_project(project)

    def list_projects(self):
        project_prefix = self.get_project_prefix()
        projects = []
        for account in self._list_accounts():
            parts = account.name.split(project_prefix)
            if len(parts) != 2:
                continue
            projects.append(parts[1])
        return projects

    def create_project(self, project):
        name = self.get_project_name(project)
        parent_name = self.get_customer_name(project.customer)
        return self._create_account(name, project.name, name, parent_name)

    def delete_project(self, project_uuid):
        project_name = '%s%s' % (self.get_project_prefix(), project_uuid)
        self._delete_account(project_name)

    def get_project_name(self, project):
        return '%s%s' % (self.get_project_prefix(), project.uuid.hex)

    def get_project_prefix(self):
        return '%s_project_' % settings.WALDUR_SLURM['ACCOUNT_NAME_PREFIX']

    def sync_allocations(self):
        slurm_allocations = set(self.list_allocations())
        waldur_allocations_map = {allocation.uuid.hex: allocation
                                  for allocation in self.get_allocation_queryset()}
        waldur_allocations = set(waldur_allocations_map.keys())

        new_allocations = waldur_allocations - slurm_allocations
        for allocation in new_allocations:
            self.create_allocation(waldur_allocations_map[allocation])

        stale_allocations = slurm_allocations - waldur_allocations
        for allocation in stale_allocations:
            self.delete_allocation(allocation)

    def list_allocations(self):
        allocation_prefix = self.get_allocation_prefix()
        allocations = []
        for account in self._list_accounts():
            parts = account.name.split(allocation_prefix)
            if len(parts) != 2:
                continue
            allocations.append(parts[1])
        return allocations

    def create_allocation(self, allocation):
        allocation_name = self.get_allocation_name(allocation)
        self._create_account(
            name=allocation_name,
            description=allocation.name,
            organization=self.get_project_name(allocation.project),
        )
        self._set_allocation_quota(allocation, allocation.cpu)

    def _set_allocation_quota(self, allocation, value):
        return self._execute_command([
            'modify', 'account', allocation.name,
            'set', 'GrpTRESMins=cpu=%s' % value
        ])

    def get_allocation_queryset(self):
        return models.Allocation.objects.filter(settings=self.settings)

    def sync_associations(self):
        waldur_associations = set()
        for allocation in self.get_allocation_queryset():
            for user in allocation.service_project_link.project.customer.get_users():
                key = (allocation.uuid.hex, user.username)
                waldur_associations.add(key)

        slurm_associations = {(association.account, association.user)
                              for association in self.list_associations()}

        new_associations = waldur_associations - slurm_associations
        for association in new_associations:
            self.create_association(*association)

        stale_associations = slurm_associations - waldur_associations
        for association in stale_associations:
            self.delete_association(*association)

    def get_allocation_name(self, allocation):
        return '%s%s' % (self.get_allocation_prefix(), allocation.uuid.hex)

    def get_allocation_prefix(self):
        return '%s_allocation_' % settings.WALDUR_SLURM['ACCOUNT_NAME_PREFIX']

    def delete_allocation(self, allocation):
        allocation_name = self.get_allocation_name(allocation)
        self._delete_account(allocation_name)

    def list_associations(self):
        output = self._execute_command(['list', 'association'])
        return [self._parse_association(line) for line in output.splitlines()]

    def _parse_association(self, line):
        parts = line.split('|')
        return SLURMAssociation(
            account=parts[1],
            user=parts[2],
        )

    def create_association(self, username, allocation):
        allocation_name = self.get_allocation_name(allocation)
        return self._execute_command(['add', 'user', username, 'account=%s' % allocation_name])

    def delete_association(self, username, allocation):
        allocation_name = self.get_allocation_name(allocation)
        return self._execute_command(['remove', 'user', username, 'account=%s' % allocation_name])

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
        return SLURMAccount(
            name=parts[0],
            description=parts[1],
            organization=parts[2],
        )

    def _execute_command(self, command):
        host = self.settings.options['hostname']
        username = self.settings.username or 'root'
        server ='%s@%s' % (username, host)
        port = str(self.settings.options['port'] or 22)
        key_path = settings.WALDUR_SLURM['PRIVATE_KEY_PATH']
        account_command = ['sacctmgr', '--immediate', '--parsable2', '--noheader']
        account_command.extend(command)
        ssh_command = ['ssh', server, '-p', port, '-i', key_path, ' '.join(account_command)]
        try:
            logging.debug('Executing SSH command: %s', ' '.join(ssh_command))
            return subprocess.check_output(ssh_command, stderr=subprocess.STDOUT)  # nosec
        except subprocess.CalledProcessError as e:
            logger.exception('Failed to execute command "%s".', ssh_command)
            six.reraise(SLURMError, e)

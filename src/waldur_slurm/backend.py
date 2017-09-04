import logging

from django.conf import settings as django_settings

from nodeconductor.structure import models as structure_models
from nodeconductor.structure import ServiceBackend
from waldur_freeipa import models as freeipa_models

from . import models
from .client import SlurmClient


logger = logging.getLogger(__name__)


class SlurmBackend(ServiceBackend):
    def __init__(self, settings):
        self.settings = settings
        self.client = SlurmClient(
            hostname=self.settings.options['hostname'],
            username=self.settings.username,
            port=self.settings.options['port'],
            key_path=django_settings.WALDUR_SLURM['PRIVATE_KEY_PATH'],
        )

    def sync(self):
        if self.get_allocation_queryset().count() == 0:
            logging.debug('Skipping SLURM service synchronization because there are no allocations.')
            return

        self.sync_customers()
        self.sync_projects()
        self.sync_allocations()
        self.sync_associations()
        self.sync_quotas()

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
        return self.list_accounts(django_settings.WALDUR_SLURM['CUSTOMER_PREFIX'])

    def create_customer(self, customer):
        customer_name = self.get_customer_name(customer)
        return self.client.create_account(customer_name, customer.name, customer_name)

    def delete_customer(self, customer_uuid):
        self.client.delete_account(self.get_customer_name(customer_uuid))

    def get_customer_name(self, customer):
        return self.get_account_name(django_settings.WALDUR_SLURM['CUSTOMER_PREFIX'], customer)

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
        return self.list_accounts(django_settings.WALDUR_SLURM['PROJECT_PREFIX'])

    def create_project(self, project):
        name = self.get_project_name(project)
        parent_name = self.get_customer_name(project.customer)
        return self.client.create_account(name, project.name, name, parent_name)

    def delete_project(self, project_uuid):
        self.client.delete_account(self.get_project_name(project_uuid))

    def get_project_name(self, project):
        return self.get_account_name(django_settings.WALDUR_SLURM['PROJECT_PREFIX'], project)

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
            self.client.delete_account(self.get_allocation_name(allocation))

    def list_allocations(self):
        return self.list_accounts(django_settings.WALDUR_SLURM['ALLOCATION_PREFIX'])

    def create_allocation(self, allocation):
        allocation_name = self.get_allocation_name(allocation)
        self.client.create_account(
            name=allocation_name,
            description=allocation.name,
            organization=self.get_project_name(allocation.project),
        )
        self.client.set_account_quota(allocation_name, allocation.cpu)

    def sync_associations(self):
        freeipa_profiles = {profile.user: profile.username
                            for profile in freeipa_models.Profile.objects.all()}

        waldur_associations = set()
        for allocation in self.get_allocation_queryset():
            for user in allocation.service_project_link.project.customer.get_users():
                if user in freeipa_profiles:
                    key = (self.get_allocation_name(allocation), freeipa_profiles[user].lower())
                    waldur_associations.add(key)

        slurm_associations = set()
        for association in self.client.list_associations():
            if association.user.startswith(django_settings.WALDUR_FREEIPA['USERNAME_PREFIX']):
                slurm_associations.add((association.account, association.user))

        new_associations = waldur_associations - slurm_associations
        for (allocation, username) in new_associations:
            self.client.create_association(username, allocation)

        stale_associations = slurm_associations - waldur_associations
        for (allocation, username) in stale_associations:
            self.client.delete_association(username, allocation)

    def sync_quotas(self):
        waldur_quotas = {
            self.get_allocation_name(allocation): allocation.cpu
            for allocation in self.get_allocation_queryset()
        }

        slurm_quotas = {
            association.account: association.value
            for association in self.client.list_associations()
            if association.user.startswith(django_settings.WALDUR_SLURM['ALLOCATION_PREFIX'])
        }

        for account, value in waldur_quotas.items():
            if slurm_quotas.get(account) != value:
                self.client.set_account_quota(account, value)

    def get_allocation_queryset(self):
        return models.Allocation.objects.filter(service_project_link__service__settings=self.settings)

    def get_allocation_name(self, allocation):
        return self.get_account_name(django_settings.WALDUR_SLURM['ALLOCATION_PREFIX'], allocation)

    def get_account_name(self, prefix, object_or_uuid):
        key = isinstance(object_or_uuid, basestring) and object_or_uuid or object_or_uuid.uuid.hex
        return '%s%s' % (prefix, key)

    def list_accounts(self, prefix):
        accounts = []
        for account in self.client.list_accounts():
            parts = account.name.split(prefix)
            if len(parts) != 2:
                continue
            accounts.append(parts[1])
        return accounts

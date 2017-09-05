import logging
import six

from django.conf import settings as django_settings

from nodeconductor.structure import ServiceBackend, ServiceBackendError
from waldur_freeipa import models as freeipa_models

from . import models
from .client import SlurmClient, SlurmError


logger = logging.getLogger(__name__)


class SlurmBackend(ServiceBackend):
    def __init__(self, settings):
        self.settings = settings
        self.client = SlurmClient(
            hostname=self.settings.options['hostname'],
            username=self.settings.username,
            port=self.settings.options['port'],
            key_path=django_settings.WALDUR_SLURM['PRIVATE_KEY_PATH'],
            use_sudo=self.settings.options['use_sudo'],
        )

    def sync(self):
        pass

    def ping(self, raise_exception=False):
        try:
            self.client.list_accounts()
        except SlurmError as e:
            if raise_exception:
                six.reraise(ServiceBackendError, e)
            return False
        else:
            return True

    def create_allocation(self, allocation):
        project = allocation.service_project_link.project
        customer_account = self.get_customer_name(project.customer)
        project_account = self.get_project_name(project)
        allocation_account = self.get_allocation_name(allocation)

        if not self.client.get_account(customer_account):
            self.create_customer(project.customer)

        if not self.client.get_account(project_account):
            self.create_project(project)

        self.client.create_account(
            name=allocation_account,
            description=allocation.name,
            organization=project_account,
        )
        self.client.set_cpu_limit(allocation_account, allocation.cpu_limit)

        freeipa_profiles = {
            profile.user: profile.username
            for profile in freeipa_models.Profile.objects.all()
        }

        for user in allocation.service_project_link.project.customer.get_users():
            username = freeipa_profiles.get(user)
            if username:
                self.client.create_association(username.lower(), allocation_account)

    def delete_allocation(self, allocation):
        self.client.delete_account(self.get_allocation_name(allocation))

        project = allocation.service_project_link.project
        if self.get_allocation_queryset().filter(project=project).count() == 0:
            self.delete_project(project)

        if self.get_allocation_queryset().filter(project__customer=project.customer).count() == 0:
            self.delete_customer(project.customer)

    def add_user(self, allocation, username):
        if not self.client.get_association(username, self.get_project_name(allocation)):
            self.client.create_association(username, self.get_project_name(allocation))

    def delete_user(self, allocation, username):
        if self.client.get_association(username, self.get_project_name(allocation)):
            self.client.delete_association(username, self.get_project_name(allocation))

    def update_allocation(self, allocation):
        self.client.set_cpu_limit(self.get_allocation_name(allocation), allocation.cpu_limit)

    def cancel_allocation(self, allocation):
        self.client.set_cpu_limit(self.get_allocation_name(allocation), allocation.cpu_usage)
        allocation.cpu_limit = allocation.cpu_usage
        allocation.is_active = False
        allocation.save()

    def sync_usage(self):
        waldur_allocations = {
            self.get_allocation_name(allocation): allocation
            for allocation in self.get_allocation_queryset()
        }
        usage = self.client.get_usage(waldur_allocations.keys())
        for account, value in usage.items():
            allocation = waldur_allocations.get(account)
            allocation.cpu_usage = value
            allocation.save()

    def create_customer(self, customer):
        customer_name = self.get_customer_name(customer)
        return self.client.create_account(customer_name, customer.name, customer_name)

    def delete_customer(self, customer_uuid):
        self.client.delete_account(self.get_customer_name(customer_uuid))

    def create_project(self, project):
        name = self.get_project_name(project)
        parent_name = self.get_customer_name(project.customer)
        return self.client.create_account(name, project.name, name, parent_name)

    def delete_project(self, project_uuid):
        self.client.delete_account(self.get_project_name(project_uuid))

    def get_allocation_queryset(self):
        return models.Allocation.objects.filter(service_project_link__service__settings=self.settings)

    def get_customer_name(self, customer):
        return self.get_account_name(django_settings.WALDUR_SLURM['CUSTOMER_PREFIX'], customer)

    def get_project_name(self, project):
        return self.get_account_name(django_settings.WALDUR_SLURM['PROJECT_PREFIX'], project)

    def get_allocation_name(self, allocation):
        return self.get_account_name(django_settings.WALDUR_SLURM['ALLOCATION_PREFIX'], allocation)

    def get_account_name(self, prefix, object_or_uuid):
        key = isinstance(object_or_uuid, basestring) and object_or_uuid or object_or_uuid.uuid.hex
        return '%s%s' % (prefix, key)

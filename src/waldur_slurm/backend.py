import logging
import six

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone

from waldur_core.structure import ServiceBackend, ServiceBackendError
from waldur_freeipa import models as freeipa_models

from . import models
from .client import SlurmClient, SlurmError
from waldur_slurm.structures import Quotas

logger = logging.getLogger(__name__)


class SlurmBackend(ServiceBackend):
    def __init__(self, settings):
        self.settings = settings
        self.client = SlurmClient(
            hostname=self.settings.options.get('hostname', 'localhost'),
            username=self.settings.username or 'root',
            port=self.settings.options.get('port', 22),
            key_path=django_settings.WALDUR_SLURM['PRIVATE_KEY_PATH'],
            use_sudo=self.settings.options.get('use_sudo', False),
        )

    def sync(self):
        self.sync_usage()

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
        self.set_resource_limits(allocation)

        freeipa_profiles = {
            profile.user: profile.username
            for profile in freeipa_models.Profile.objects.all()
        }

        for user in allocation.service_project_link.project.customer.get_users():
            username = freeipa_profiles.get(user)
            if username:
                self.add_user(allocation, username.lower())

    def delete_allocation(self, allocation):
        account = self.get_allocation_name(allocation)
        if self.client.get_account(account):
            self.client.delete_account(account)

        project = allocation.service_project_link.project
        if self.get_allocation_queryset().filter(project=project).count() == 0:
            self.delete_project(project)

        if self.get_allocation_queryset().filter(project__customer=project.customer).count() == 0:
            self.delete_customer(project.customer)

    def add_user(self, allocation, username):
        """
        Create association between user and SLURM account if it does not exist yet.
        """
        account = self.get_allocation_name(allocation)
        default_account = self.settings.options.get('default_account')
        if not self.client.get_association(username, account):
            self.client.create_association(username, account, default_account)

    def delete_user(self, allocation, username):
        """
        Delete association between user and SLURM account if it exists.
        """
        account = self.get_allocation_name(allocation)
        if self.client.get_association(username, account):
            self.client.delete_association(username, account)

    def set_resource_limits(self, allocation):
        quotas = Quotas(allocation.cpu_limit, allocation.gpu_limit, allocation.ram_limit)
        self.client.set_resource_limits(self.get_allocation_name(allocation), quotas)

    def cancel_allocation(self, allocation):
        allocation.cpu_limit = allocation.cpu_usage
        allocation.gpu_limit = allocation.gpu_usage
        allocation.ram_limit = allocation.ram_usage

        self.set_resource_limits(allocation)

        allocation.is_active = False
        allocation.save()

    def sync_usage(self):
        waldur_allocations = {
            self.get_allocation_name(allocation): allocation
            for allocation in self.get_allocation_queryset()
        }
        report = self.client.get_usage_report(waldur_allocations.keys())
        for account, usage in report.items():
            allocation = waldur_allocations.get(account)
            if not allocation:
                logger.debug('Skipping usage report for account %s because it is not managed under Waldur', account)
                continue
            self._update_quotas(allocation, usage)

    def pull_allocation(self, allocation):
        account = self.get_allocation_name(allocation)
        report = self.client.get_usage_report([account])
        usage = report.get(account)
        if not usage:
            logger.debug('Skipping usage report for account %s because it is not managed under Waldur', account)
            return
        self._update_quotas(allocation, usage)

    @transaction.atomic()
    def _update_quotas(self, allocation, usage):
        quotas = usage.pop('TOTAL_ACCOUNT_USAGE')
        allocation.cpu_usage = quotas.cpu
        allocation.gpu_usage = quotas.gpu
        allocation.ram_usage = quotas.ram
        allocation.save(update_fields=['cpu_usage', 'gpu_usage', 'ram_usage'])

        usernames = usage.keys()
        usermap = {
            profile.username: profile.user
            for profile in freeipa_models.Profile.objects.filter(username__in=usernames)
        }

        for username, quotas in usage.items():
            models.AllocationUsage.objects.update_or_create(
                allocation=allocation,
                username=username,
                year=timezone.now().year,
                month=timezone.now().month,
                defaults={
                    'cpu_usage': quotas.cpu,
                    'gpu_usage': quotas.gpu,
                    'ram_usage': quotas.ram,
                    'user': usermap.get(username),
                })

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

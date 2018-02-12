import math

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker

from waldur_core.structure import models as structure_models
from waldur_freeipa import models as freeipa_models

from waldur_slurm import utils
from waldur_slurm.base import BatchProvider
from waldur_slurm.client import SlurmClient
from waldur_slurm.client_moab import MoabClient
from waldur_slurm.structures import Quotas


class SlurmService(structure_models.Service):
    projects = models.ManyToManyField(structure_models.Project,
                                      related_name='+', through='SlurmServiceProjectLink')

    @staticmethod
    def get_provider(service_settings):
        batch_service = service_settings.options.get('batch_service', 'SLURM')

        if batch_service == 'SLURM':
            return SLURM

        if batch_service == 'MOAB':
            return MOAB

    def get_instance_provider(self):
        return SlurmService.get_provider(self.settings)

    class Meta:
        unique_together = ('customer', 'settings')
        verbose_name = _('SLURM provider')
        verbose_name_plural = _('SLURM providers')

    @classmethod
    def get_url_name(cls):
        return 'slurm'


class SlurmServiceProjectLink(structure_models.ServiceProjectLink):
    service = models.ForeignKey(SlurmService)

    class Meta(structure_models.ServiceProjectLink.Meta):
        verbose_name = _('SLURM provider project link')
        verbose_name_plural = _('SLURM provider project links')

    @classmethod
    def get_url_name(cls):
        return 'slurm-spl'


class Allocation(structure_models.NewResource):
    service_project_link = models.ForeignKey(
        SlurmServiceProjectLink, related_name='allocations', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    tracker = FieldTracker()

    cpu_limit = models.BigIntegerField(default=-1)
    cpu_usage = models.BigIntegerField(default=0)

    gpu_limit = models.BigIntegerField(default=-1)
    gpu_usage = models.BigIntegerField(default=0)

    ram_limit = models.BigIntegerField(default=-1)
    ram_usage = models.BigIntegerField(default=0)

    deposit_limit = models.DecimalField(max_digits=6, decimal_places=0, default=-1)
    deposit_usage = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    @classmethod
    def get_url_name(cls):
        return 'slurm-allocation'

    def usage_changed(self):
        return any(self.tracker.has_changed(field) for field in utils.FIELD_NAMES)

    @classmethod
    def get_backend_fields(cls):
        return super(Allocation, cls).get_backend_fields() + ('cpu_usage', 'gpu_usage', 'ram_usage')

    def get_price(self, package):
        return self.service_project_link.service.get_instance_provider().\
            get_price(self, package)

    def get_details(self):
        return self.service_project_link.service.get_instance_provider(). \
            get_details(self)

    def get_settings_if_need_calculate_limits(self):
        if self.service_project_link.service.get_instance_provider() == MOAB:
            return self.service_project_link.service.settings


class AllocationUsage(models.Model):
    class Permissions(object):
        customer_path = 'allocation__service_project_link__project__customer'
        project_path = 'allocation__service_project_link__project'
        service_path = 'allocation__service_project_link__service'

    class Meta(object):
        ordering = ['allocation']

    allocation = models.ForeignKey(Allocation)
    username = models.CharField(max_length=32)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, blank=True, null=True)

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])

    cpu_usage = models.BigIntegerField(default=0)
    ram_usage = models.BigIntegerField(default=0)
    gpu_usage = models.BigIntegerField(default=0)


class SLURM(BatchProvider):
    @staticmethod
    def get_client_class():
        return SlurmClient

    @staticmethod
    def get_price(allocation, package):
        minutes_in_hour = 60
        mb_in_gb = 1024
        cpu_price = int(math.ceil(1.0 * allocation.cpu_usage / minutes_in_hour)) * package.cpu_price
        gpu_price = int(math.ceil(1.0 * allocation.gpu_usage / minutes_in_hour)) * package.gpu_price
        ram_price = int(math.ceil(1.0 * allocation.ram_usage / mb_in_gb)) * package.ram_price
        return cpu_price + gpu_price + ram_price

    @staticmethod
    def get_details(allocation):
        return {
            'cpu_usage': allocation.cpu_usage,
            'gpu_usage': allocation.gpu_usage,
            'ram_usage': allocation.ram_usage,
        }

    @staticmethod
    def get_quotas(allocation):
        return Quotas(cpu=allocation.cpu_limit,
                      gpu=allocation.gpu_limit,
                      ram=allocation.ram_limit)

    @staticmethod
    @transaction.atomic()
    def update_allocation_usage(allocation, usage):
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
            AllocationUsage.objects.update_or_create(
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


class MOAB(BatchProvider):
    @staticmethod
    def get_client_class():
        return MoabClient

    @staticmethod
    def get_price(allocation, package):
        return allocation.deposit_usage

    @staticmethod
    def get_details(allocation):
        return {
            'deposit_usage': allocation.deposit_usage,
        }

    @staticmethod
    def get_quotas(allocation):
        return Quotas(deposit=allocation.deposit_limit)

    @staticmethod
    @transaction.atomic()
    def update_allocation_usage(allocation, quotas):
        allocation.deposit_usage = quotas.deposit
        allocation.save(update_fields=['deposit_usage'])

        AllocationUsage.objects.update_or_create(
            allocation=allocation,
            defaults={
                'year': timezone.now().year,
                'month': timezone.now().month,
                'cpu_usage': quotas.cpu,
                'gpu_usage': quotas.gpu,
                'ram_usage': quotas.ram,
            })


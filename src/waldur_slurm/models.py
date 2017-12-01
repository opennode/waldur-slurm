from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker

from waldur_core.structure import models as structure_models

from . import utils


class SlurmService(structure_models.Service):
    projects = models.ManyToManyField(structure_models.Project,
                                      related_name='+', through='SlurmServiceProjectLink')

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

    cpu_limit = models.IntegerField(default=-1)
    cpu_usage = models.IntegerField(default=0)

    gpu_limit = models.IntegerField(default=-1)
    gpu_usage = models.IntegerField(default=0)

    ram_limit = models.IntegerField(default=-1)
    ram_usage = models.IntegerField(default=0)

    @classmethod
    def get_url_name(cls):
        return 'slurm-allocation'

    def usage_changed(self):
        return any(self.tracker.has_changed(field) for field in utils.FIELD_NAMES)

    @classmethod
    def get_backend_fields(cls):
        return super(Allocation, cls).get_backend_fields() + ('cpu_usage', 'gpu_usage', 'ram_usage')


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

    cpu_usage = models.IntegerField(default=0)
    ram_usage = models.IntegerField(default=0)
    gpu_usage = models.IntegerField(default=0)

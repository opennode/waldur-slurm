from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker

from nodeconductor.structure import models as structure_models

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

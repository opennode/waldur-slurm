from django.db import models
from django.utils.translation import ugettext_lazy as _

from nodeconductor.structure import models as structure_models


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
    cpu_limit = models.IntegerField(default=0)
    cpu_usage = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    @classmethod
    def get_url_name(cls):
        return 'slurm-allocation'

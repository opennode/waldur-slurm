from nodeconductor.core import filters as core_filters
from nodeconductor.structure import filters as structure_filters

from . import models


class SlurmServiceProjectLinkFilter(structure_filters.BaseServiceProjectLinkFilter):
    service = core_filters.URLFilter(view_name='slurm-detail', name='service__uuid')

    class Meta(structure_filters.BaseServiceProjectLinkFilter.Meta):
        model = models.SlurmServiceProjectLink


class AllocationFilter(structure_filters.BaseResourceFilter):
    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Allocation
        fields = structure_filters.BaseResourceFilter.Meta.fields + ('is_active',)

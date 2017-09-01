from nodeconductor.core import filters as core_filters
from nodeconductor.structure import filters as structure_filters

from . import models


class SLURMServiceProjectLinkFilter(structure_filters.BaseServiceProjectLinkFilter):
    service = core_filters.URLFilter(view_name='slurm-detail', name='service__uuid')

    class Meta(structure_filters.BaseServiceProjectLinkFilter.Meta):
        model = models.SLURMServiceProjectLink

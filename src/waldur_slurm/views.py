import six

from nodeconductor.structure import views as structure_views

from . import filters, models, serializers


class SlurmServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.SlurmService.objects.all()
    serializer_class = serializers.ServiceSerializer


class SlurmServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.SlurmServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer
    filter_class = filters.SlurmServiceProjectLinkFilter


class AllocationViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass,
                                           structure_views.ResourceViewSet)):
    queryset = models.Allocation.objects.all()
    serializer_class = serializers.AllocationSerializer
    filter_class = filters.AllocationFilter

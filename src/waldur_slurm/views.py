import six

from nodeconductor.structure import views as structure_views

from . import filters, models, serializers


class SLURMServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.SLURMService.objects.all()
    serializer_class = serializers.ServiceSerializer


class SLURMServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.SLURMServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer
    filter_class = filters.SLURMServiceProjectLinkFilter


class AllocationViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass,
                                           structure_views.ResourceViewSet)):
    queryset = models.Allocation.objects.all()
    serializer_class = serializers.AllocationSerializer
    filter_class = filters.AllocationFilter

from nodeconductor.structure import views as structure_views

from . import filters, models, serializers


class SLURMServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.SLURMService.objects.all()
    serializer_class = serializers.ServiceSerializer


class SLURMServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.SLURMServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer
    filter_class = filters.SLURMServiceProjectLinkFilter

import six

from rest_framework import decorators, response, status

from nodeconductor.structure import views as structure_views
from nodeconductor.structure import permissions as structure_permissions

from . import executors, filters, models, serializers


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

    create_permissions = [structure_permissions.is_owner]
    create_executor = executors.AllocationCreateExecutor

    destroy_permissions = [structure_permissions.is_staff]
    delete_executor = executors.AllocationDeleteExecutor

    update_permissions = [structure_permissions.is_owner]
    update_executor = executors.AllocationUpdateExecutor

    @decorators.detail_route(methods=['post'])
    def cancel(self, request, uuid=None):
        allocation = self.get_object()
        allocation.get_backend().cancel_allocation(allocation)
        return response.Response(status=status.HTTP_200_OK)

    cancel_permissions = [structure_permissions.is_owner]

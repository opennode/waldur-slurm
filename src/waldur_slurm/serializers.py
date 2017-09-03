from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers as rf_serializers

from nodeconductor.core import serializers as core_serializers
from nodeconductor.structure import serializers as structure_serializers

from . import models


class ServiceSerializer(core_serializers.ExtraFieldOptionsMixin,
                        core_serializers.RequiredFieldsMixin,
                        structure_serializers.BaseServiceSerializer):
    SERVICE_ACCOUNT_FIELDS = {
        'username': '',
    }
    SERVICE_ACCOUNT_EXTRA_FIELDS = {
        'hostname': _('Hostname or IP address'),
        'port': '',
    }

    class Meta(structure_serializers.BaseServiceSerializer.Meta):
        model = models.SLURMService
        required_fields = ('hostname', 'username')
        extra_field_options = {
            'username': {
                'default_value': 'root',
            },
        }


class ServiceProjectLinkSerializer(structure_serializers.BaseServiceProjectLinkSerializer):
    class Meta(structure_serializers.BaseServiceProjectLinkSerializer.Meta):
        model = models.SLURMServiceProjectLink
        extra_kwargs = {
            'service': {'lookup_field': 'uuid', 'view_name': 'slurm-detail'},
        }


class AllocationSerializer(structure_serializers.BaseResourceSerializer):
    service = rf_serializers.HyperlinkedRelatedField(
        source='service_project_link.service',
        view_name='slurm-detail',
        read_only=True,
        lookup_field='uuid')

    service_project_link = rf_serializers.HyperlinkedRelatedField(
        view_name='slurm-spl-detail',
        queryset=models.SLURMServiceProjectLink.objects.all())

    class Meta(structure_serializers.BaseResourceSerializer.Meta):
        model = models.Allocation
        fields = structure_serializers.BaseResourceSerializer.Meta.fields + ('cpu',)

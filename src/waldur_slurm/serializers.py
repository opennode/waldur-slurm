from django.utils.translation import ugettext_lazy as _

from nodeconductor.core import serializers as core_serializers
from nodeconductor.structure import serializers as structure_serializers

from . import models


class ServiceSerializer(core_serializers.ExtraFieldOptionsMixin,
                        core_serializers.RequiredFieldsMixin,
                        structure_serializers.BaseServiceSerializer):
    SERVICE_ACCOUNT_FIELDS = {
        'hostname': _('Hostname or IP address'),
        'username': _('User username'),
        'password': _('User password'),
    }

    class Meta(structure_serializers.BaseServiceSerializer.Meta):
        model = models.SLURMService
        required_fields = ('hostname', 'username', 'password')


class ServiceProjectLinkSerializer(structure_serializers.BaseServiceProjectLinkSerializer):
    class Meta(structure_serializers.BaseServiceProjectLinkSerializer.Meta):
        model = models.SLURMServiceProjectLink
        extra_kwargs = {
            'service': {'lookup_field': 'uuid', 'view_name': 'slurm-detail'},
        }

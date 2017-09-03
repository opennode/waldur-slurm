from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models import signals


class SLURMConfig(AppConfig):
    name = 'waldur_slurm'
    verbose_name = 'SLURM'
    service_name = 'SLURM'

    def ready(self):
        from nodeconductor.structure import SupportedServices

        from .backend import SLURMBackend
        SupportedServices.register_backend(SLURMBackend)

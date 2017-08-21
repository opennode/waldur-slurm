from __future__ import unicode_literals

from django.apps import AppConfig


class SLURMConfig(AppConfig):
    name = 'waldur_slurm'
    verbose_name = 'SLURM'

    def ready(self):
        from nodeconductor.structure import SupportedServices

        from .backend import SLURMBackend
        SupportedServices.register_backend(SLURMBackend)

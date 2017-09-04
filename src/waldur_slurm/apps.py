from __future__ import unicode_literals

from django.apps import AppConfig


class SlurmConfig(AppConfig):
    name = 'waldur_slurm'
    verbose_name = 'SLURM'
    service_name = 'SLURM'

    def ready(self):
        from nodeconductor.structure import SupportedServices

        from .backend import SlurmBackend
        SupportedServices.register_backend(SlurmBackend)

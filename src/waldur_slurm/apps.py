from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models import signals


class SlurmConfig(AppConfig):
    name = 'waldur_slurm'
    verbose_name = 'SLURM'
    service_name = 'SLURM'

    def ready(self):
        from nodeconductor.structure import SupportedServices
        from nodeconductor.structure import models as structure_models
        from nodeconductor.structure import signals as structure_signals
        from waldur_freeipa import models as freeipa_models

        from .backend import SlurmBackend
        from . import handlers

        SupportedServices.register_backend(SlurmBackend)

        signals.post_save.connect(
            handlers.process_user_creation,
            sender=freeipa_models.Profile,
            dispatch_uid='waldur_slurm.handlers.process_user_creation',
        )

        signals.pre_delete.connect(
            handlers.process_user_deletion,
            sender=freeipa_models.Profile,
            dispatch_uid='waldur_slurm.handlers.process_user_deletion',
        )

        structure_models_with_roles = (structure_models.Customer, structure_models.Project)
        for model in structure_models_with_roles:
            structure_signals.structure_role_granted.connect(
                handlers.process_role_granted,
                sender=model,
                dispatch_uid='waldur_slurm.handlers.process_role_granted.%s' % model.__class__,
            )

            structure_signals.structure_role_revoked.connect(
                handlers.process_role_revoked,
                sender=model,
                dispatch_uid='waldur_slurm.handlers.process_role_revoked.%s' % model.__class__,
            )

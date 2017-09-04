from celery import shared_task

from nodeconductor.core import utils as core_utils
from nodeconductor.structure import models as structure_models
from . import models


def get_user_allocations(user):
    permissions = structure_models.ProjectPermission.objects.filter(user=user, is_active=True)
    projects = permissions.values_list('project_id', flat=True)
    return models.Allocation.objects.filter(service_project_link__project__in=projects)


@shared_task(name='waldur_slurm.add_user')
def add_user(serialized_profile):
    profile = core_utils.deserialize_instance(serialized_profile)
    for allocation in get_user_allocations(profile.user):
        allocation.get_backend().add_user(allocation, profile.username)


@shared_task(name='waldur_slurm.delete_user')
def delete_user(serialized_profile):
    profile = core_utils.deserialize_instance(serialized_profile)
    for allocation in get_user_allocations(profile.user):
        allocation.get_backend().delete_user(allocation, profile.username)


@shared_task(name='waldur_slurm.sync_usage')
def sync_usage():
    for settings in structure_models.ServiceSettings.objects.filter(type='SLURM'):
        settings.sync_usage()

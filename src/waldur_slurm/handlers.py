from django.db.models import Sum

from nodeconductor.core import utils as core_utils
from waldur_freeipa import models as freeipa_models

from . import models, tasks, utils


def process_user_creation(sender, instance, created=False, **kwargs):
    if not created:
        return
    tasks.add_user.delay(core_utils.serialize_instance(instance))


def process_user_deletion(sender, instance, **kwargs):
    tasks.delete_user.delay(core_utils.serialize_instance(instance))


def process_role_granted(sender, structure, user, role, **kwargs):
    try:
        freeipa_profile = freeipa_models.Profile.objects.get(user=user)
        tasks.add_user.delay(core_utils.serialize_instance(freeipa_profile))
    except freeipa_models.Profile.DoesNotExist:
        pass


def process_role_revoked(sender, structure, user, role, **kwargs):
    try:
        freeipa_profile = freeipa_models.Profile.objects.get(user=user)
        tasks.delete_user.delay(core_utils.serialize_instance(freeipa_profile))
    except freeipa_models.Profile.DoesNotExist:
        pass


def update_quotas_on_allocation_usage_update(sender, instance, created=False, **kwargs):
    if created:
        return

    allocation = instance
    if not allocation.usage_changed():
        return

    project = allocation.service_project_link.project
    update_quotas(project, models.Allocation.Permissions.project_path)
    update_quotas(project.customer, models.Allocation.Permissions.customer_path)


def update_quotas(scope, path):
    qs = models.Allocation.objects.filter(**{path: scope}).values(path)
    for quota in utils.FIELD_NAMES:
        qs = qs.annotate(**{'total_%s' % quota: Sum(quota)})
    qs = list(qs)[0]

    for quota in utils.FIELD_NAMES:
        scope.set_quota_usage(utils.MAPPING[quota], qs['total_%s' % quota])

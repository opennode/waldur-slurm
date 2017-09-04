from nodeconductor.core import utils as core_utils
from waldur_freeipa import models as freeipa_models

from . import tasks


def process_user_creation(sender, instance, created=False, **kwargs):
    if not created:
        return
    tasks.add_user.delay(core_utils.serialize_instance(instance))


def process_user_deletion(sender, instance, **kwargs):
    tasks.delete_user.delay(core_utils.serialize_instance(instance))


def process_role_granted(sender, instance, **kwargs):
    try:
        freeipa_profile = freeipa_models.Profile.objects.get(user=instance)
        tasks.add_user.delay(core_utils.serialize_instance(freeipa_profile))
    except freeipa_models.Profile.DoesNotExist:
        pass


def process_role_revoked(sender, instance, **kwargs):
    try:
        freeipa_profile = freeipa_models.Profile.objects.get(user=instance)
        tasks.delete_user.delay(core_utils.serialize_instance(freeipa_profile))
    except freeipa_models.Profile.DoesNotExist:
        pass

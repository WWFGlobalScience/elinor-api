from django import urls
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .utils.email import (
    email_elinor_admins_flag,
    email_assessment_admins_flag,
    email_assessment_flagger,
)
from .models import (
    Assessment,
    AssessmentFlag,
    Collaborator,
    Document,
    ManagementArea,
    Profile,
)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    profile, created = Profile.objects.get_or_create(user=instance)
    profile.save()


def move_model_file(instance, filefield):
    file = getattr(instance, filefield)
    model = type(instance).__name__
    if not file:
        return
    oldpath = file.name
    newpath = f"{model}/{str(instance.pk)}/{oldpath.split('/')[-1]}"
    if newpath != oldpath and default_storage.exists(oldpath):
        default_storage.save(newpath, file)
        default_storage.delete(oldpath)
        file.name = newpath
        instance.save()


def delete_model_file(instance, filefield):
    file = getattr(instance, filefield)
    if not file:
        return
    path = file.name
    if default_storage.exists(path):
        default_storage.delete(path)


@receiver(post_save, sender=Assessment)
def move_ap_files(sender, instance, created, **kwargs):
    move_model_file(instance, "management_plan_file")


@receiver(post_save, sender=Document)
def move_doc_files(sender, instance, created, **kwargs):
    move_model_file(instance, "file")


@receiver(post_save, sender=ManagementArea)
def move_ma_files(sender, instance, created, **kwargs):
    move_model_file(instance, "import_file")
    move_model_file(instance, "map_image")


@receiver(post_delete, sender=Assessment)
def delete_ap_files(sender, instance, **kwargs):
    delete_model_file(instance, "management_plan_file")


@receiver(post_delete, sender=Document)
def delete_doc_files(sender, instance, **kwargs):
    delete_model_file(instance, "file")


@receiver(post_delete, sender=ManagementArea)
def delete_ma_files(sender, instance, **kwargs):
    delete_model_file(instance, "import_file")
    delete_model_file(instance, "map_image")


@receiver(post_save, sender=AssessmentFlag)
def notify_assessment_flagged(sender, instance, created, **kwargs):
    if created:
        reverse_str = f"admin:api_assessment_change"
        url = urls.reverse(reverse_str, args=[instance.assessment.pk])
        admin_link = f"{settings.API_DOMAIN}{url}"
        assessment_admins = Collaborator.objects.filter(
            assessment=instance.assessment, role=Collaborator.ADMIN
        )
        admin_emails = [a.user.email for a in assessment_admins]

        email_elinor_admins_flag(instance, admin_link)
        email_assessment_admins_flag(instance, admin_emails)
        email_assessment_flagger(instance)

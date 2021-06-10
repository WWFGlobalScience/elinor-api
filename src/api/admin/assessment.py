from django.contrib import admin
from .base import BaseAdmin
from ..models.assessment import *
from ..utils.assessment import log_assessment_change


class AssessmentChangeInline(admin.TabularInline):
    model = AssessmentChange
    exclude = ("created_by", "updated_by")
    readonly_fields = ("user", "event_on", "event_type")
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Assessment)
class AssessmentAdmin(BaseAdmin):
    list_display = [
        "name",
        "status",
        "data_policy",
        "year",
        "management_area_version",
    ] + BaseAdmin.list_display
    search_fields = ["name", "management_area__name", "organization", ]
    list_filter = ["status", "data_policy", "year", "management_area_version"]
    inlines = [AssessmentChangeInline]

    def save_model(self, request, obj, form, change):
        if change:
            original_assessment = self.model.objects.get(pk=obj.pk)
            editor = request.user
            super().save_model(request, obj, form, change)
            log_assessment_change(original_assessment, obj, editor)
        else:
            super().save_model(request, obj, form, change)


@admin.register(Collaborator)
class CollaboratorAdmin(BaseAdmin):
    list_display = ["selfstr", "assessment", "user", "role"] + BaseAdmin.list_display
    search_fields = [
        "assessment__name",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    list_filter = ["role"]

    @admin.display(description="collaborator", ordering="assessment__name")
    def selfstr(self, obj):
        return obj.__str__()

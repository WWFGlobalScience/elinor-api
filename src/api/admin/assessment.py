from django.contrib import admin
from .base import BaseAdmin
from ..models.assessment import *
from ..utils.assessment import log_ap_change


@admin.register(Assessment)
class AssessmentAdmin(BaseAdmin):
    list_display = ["name"] + BaseAdmin.list_display
    search_fields = ["name"]


class AssessmentPeriodChangeInline(admin.TabularInline):
    model = AssessmentPeriodChange
    exclude = ("created_by", "updated_by")
    readonly_fields = ("user", "event_on", "event_type")
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AssessmentPeriod)
class AssessmentPeriodAdmin(BaseAdmin):
    list_display = [
        "selfstr",
        "status",
        "data_policy",
        "year",
        "management_area",
    ] + BaseAdmin.list_display
    search_fields = ["assessment__name", "management_area__name"]
    list_filter = ["status", "data_policy", "year", "management_area"]
    inlines = [AssessmentPeriodChangeInline]

    @admin.display(description="assessment period", ordering="assessment__name")
    def selfstr(self, obj):
        return obj.__str__()

    def save_model(self, request, obj, form, change):
        if change:
            original_ap = self.model.objects.get(pk=obj.pk)
            editor = request.user
            super().save_model(request, obj, form, change)
            log_ap_change(original_ap, obj, editor)
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

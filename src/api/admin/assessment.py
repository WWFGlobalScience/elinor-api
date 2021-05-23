from django.contrib import admin
from .base import BaseAdmin
from ..models.assessment import *


@admin.register(Assessment)
class AssessmentAdmin(BaseAdmin):
    search_fields = ["name"]


@admin.register(AssessmentPeriod)
class AssessmentPeriodAdmin(BaseAdmin):
    list_display = ["selfstr", "status", "data_policy", "year", "management_area"]
    search_fields = ["assessment__name", "management_area__name"]
    list_filter = ["status", "data_policy", "year", "management_area"]

    @admin.display(description="assessment period", ordering="assessment__name")
    def selfstr(self, obj):
        return obj.__str__()


@admin.register(Collaborator)
class CollaboratorAdmin(BaseAdmin):
    list_display = ["selfstr", "assessment_period", "user", "role"]
    search_fields = [
        "assessment_period__assessment__name",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    list_filter = ["role"]

    @admin.display(
        description="collaborator", ordering="assessment_period__assessment__name"
    )
    def selfstr(self, obj):
        return obj.__str__()

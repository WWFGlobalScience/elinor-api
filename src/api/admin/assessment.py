from django.contrib import admin
from .base import BaseAdmin
from ..models.assessment import *
from ..utils.assessment import enforce_required_attributes, log_assessment_change


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


class SurveyAnswerLikertInline(admin.TabularInline):
    model = SurveyAnswerLikert
    exclude = ("created_by", "updated_by")
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(BaseAdmin):
    list_display = [
        "name",
        "status",
        "data_policy",
        "year",
        "management_area",
    ] + BaseAdmin.list_display
    search_fields = [
        "name",
        "management_area__name",
        "organization__name",
    ]
    list_filter = ["status", "data_policy", "year", "management_area"]
    inlines = [SurveyAnswerLikertInline, AssessmentChangeInline]

    def save_model(self, request, obj, form, change):
        if change:
            original_assessment = self.model.objects.get(pk=obj.pk)
            editor = request.user
            super().save_model(request, obj, form, change)
            log_assessment_change(original_assessment, obj, editor)
        else:
            super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        enforce_required_attributes(obj)


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


@admin.register(SurveyQuestionLikert)
class SurveyQuestionLikertAdmin(BaseAdmin):
    list_display = ["key", "attribute", "number"] + BaseAdmin.list_display


@admin.register(SurveyAnswerLikert)
class SurveyAnswerLikertAdmin(BaseAdmin):
    list_display = ["question", "assessment", "choice"] + BaseAdmin.list_display

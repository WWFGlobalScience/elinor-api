from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .base import BaseAdmin
from ..models.assessment import *
from ..utils.assessment import enforce_required_attributes, log_assessment_change


class SurveyAnswerLikertInline(admin.TabularInline):
    model = SurveyAnswerLikert
    exclude = ("created_by", "updated_by")
    extra = 0


class AssessmentFlagInline(admin.TabularInline):
    model = AssessmentFlag
    exclude = ("created_by", "updated_by")
    extra = 0


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
class AssessmentAdmin(BaseAdmin, TranslationAdmin):
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
    inlines = [SurveyAnswerLikertInline, AssessmentFlagInline, AssessmentChangeInline]

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


@admin.register(AssessmentFlag)
class AssessmentFlagAdmin(BaseAdmin):
    list_display = [
        "selfstr",
        "flag_type_integrated",
        "created_on",
        "datetime_resolved",
        "reportername",
    ]
    search_fields = [
        "assessment__name",
        "reporter__username",
        "reporter__first_name",
        "reporter__last_name",
        "reporter__email",
    ]
    list_filter = ["flag_type"]

    @admin.display(description="flag", ordering="assessment__name")
    def selfstr(self, obj):
        return obj.__str__()

    @admin.display(description="reporter", ordering="reporter__username")
    def reportername(self, obj):
        return obj.reporter.username

    @admin.display(description="type", ordering="flag_type")
    def flag_type_integrated(self, obj):
        if obj.flag_type_other != "":
            return obj.flag_type_other
        return obj.flag_type


@admin.register(SurveyQuestionLikert)
class SurveyQuestionLikertAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["key", "attribute", "number"] + BaseAdmin.list_display


@admin.register(SurveyAnswerLikert)
class SurveyAnswerLikertAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["question", "assessment", "choice"] + BaseAdmin.list_display

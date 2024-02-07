from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .base import BaseAdmin
from ..models import SurveyQuestionLikert, SurveyAnswerLikert


@admin.register(SurveyQuestionLikert)
class SurveyQuestionLikertAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["key", "attribute", "number"] + BaseAdmin.list_display


@admin.register(SurveyAnswerLikert)
class SurveyAnswerLikertAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["question", "assessment", "choice"] + BaseAdmin.list_display
    search_fields = ["question__key", "assessment__name"]

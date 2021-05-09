from django.contrib import admin
from .base import BaseAdmin
from ..models.assessment import *


@admin.register(Assessment)
class AssessmentAdmin(BaseAdmin):
    list_display = [
        "name",
        "management_area",
        "count_manager",
        "count_personnel",
        "count_government",
        "count_committee",
        "count_community",
    ]
    search_fields = ["name", "management_area__name"]
    list_filter = ["management_area"]

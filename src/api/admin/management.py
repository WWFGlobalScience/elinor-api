from django.contrib import admin
from .base import BaseAdmin, CountryListFilter, country_flag, linkify
from ..models.management import *


class ManagementAreaZoneInline(admin.StackedInline):
    model = ManagementAreaZone
    extra = 0


@admin.register(ManagementArea)
class ManagementAreaAdmin(BaseAdmin):
    list_display = [
        "name",
        "version_date",
        "governance_type",
        country_flag,
    ] + BaseAdmin.list_display
    search_fields = ["name", "governance_type__name"]
    list_filter = ("governance_type", CountryListFilter)
    filter_horizontal = ["regions", "stakeholder_groups", "support_sources"]
    inlines = [ManagementAreaZoneInline]


@admin.register(ManagementAreaZone)
class ManagementAreaZoneAdmin(BaseAdmin):
    list_display = ["name", "access_level"] + BaseAdmin.list_display
    search_fields = ["name"]
    list_filter = ("access_level",)

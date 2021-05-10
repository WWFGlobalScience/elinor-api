import csv
import datetime
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.gis.admin import OSMGeoAdmin
from django.http import HttpResponse
from django.utils.html import format_html
from ..models.base import *


UserModel = get_user_model()


def lookup_field_from_choices(field_obj, value):
    choices = getattr(field_obj, "choices")
    if choices is not None and len(choices) > 0:
        choices_dict = dict(choices)
        try:
            value = choices_dict[value]
        except KeyError:
            pass

    return value


def export_model_as_csv(modeladmin, request, queryset, field_list):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s-%s-export_%s.csv" % (
        __package__.lower(),
        queryset.model.__name__.lower(),
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    )

    writer = csv.writer(response)
    writer.writerow(
        [admin.utils.label_for_field(f, queryset.model, modeladmin) for f in field_list]
    )

    for obj in queryset:
        csv_line_values = []
        for field in field_list:
            field_obj, attr, value = admin.utils.lookup_field(field, obj, modeladmin)
            if field_obj is not None and hasattr(field_obj, "choices"):
                value = lookup_field_from_choices(field_obj, value)
            csv_line_values.append(str(value).strip())

        writer.writerow(csv_line_values)

    return response


def export_model_display_as_csv(modeladmin, request, queryset):
    if hasattr(modeladmin, "exportable_fields"):
        field_list = modeladmin.exportable_fields
    else:
        field_list = list(modeladmin.list_display[:])
        if "action_checkbox" in field_list:
            field_list.remove("action_checkbox")

    return export_model_as_csv(modeladmin, request, queryset, field_list)


def export_model_all_as_csv(modeladmin, request, queryset):
    field_list = [
        f.name
        for f in queryset.model._meta.get_fields()
        if f.concrete
        and (not f.is_relation or f.one_to_one or (f.many_to_one and f.related_model))
    ]
    if hasattr(modeladmin, "exportable_fields"):
        added_fields = [f for f in modeladmin.exportable_fields if f not in field_list]
        field_list = field_list + added_fields

    return export_model_as_csv(modeladmin, request, queryset, field_list)


export_model_display_as_csv.short_description = (
    "Export selected %(verbose_name_plural)s to CSV (display)"
)
export_model_all_as_csv.short_description = (
    "Export selected %(verbose_name_plural)s to CSV (all fields)"
)


@admin.display(description="country", ordering="country", )
def country_flag(obj):
    _country = obj.country
    if _country is None:
        return ""
    return format_html(
        '<img src="{}"> {}'.format(_country.flag, _country.name)
    )


class BaseAdmin(OSMGeoAdmin):
    list_select_related = True
    actions = (export_model_display_as_csv, export_model_all_as_csv)


class BaseChoiceAdmin(admin.ModelAdmin):
    list_display = ["name",]
    ordering = ["name",]


admin.site.unregister(UserModel)


class UserProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


@admin.register(UserModel)
class UserProfileAdmin(UserAdmin, BaseAdmin):
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

    def save_formset(self, request, form, formset, change):
        formset.save()
        for f in formset.forms:
            obj = f.instance
            obj.updated_by = request.user
            obj.save()


class CountryListFilter(admin.SimpleListFilter):
    title = "Country"
    parameter_name = "country"

    def lookups(self, request, model_admin):
        countries = []
        for o in model_admin.model.objects.all():
            countries.append(getattr(o, self.parameter_name))
        countries = set(countries)
        return [
            (c.code, format_html("<img src='{}'> {}".format(c.flag, c.name)))
            for c in countries
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country=self.value())
        else:
            return queryset


@admin.register(GovernanceType)
class GovernanceTypeAdmin(BaseChoiceAdmin):
    pass


@admin.register(Region)
class RegionAdmin(BaseChoiceAdmin):
    list_display = ["name", country_flag]
    list_filter = (CountryListFilter,)


@admin.register(ManagementArea)
class ManagementAreaAdmin(BaseAdmin):
    list_display = ["name", "date_established", "governance_type", country_flag, "region"]
    search_fields = ["name", "governance_type__name", "region__name"]
    list_filter = ("governance_type", CountryListFilter,)

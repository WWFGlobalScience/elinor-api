import csv
import datetime
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.gis.admin import OSMGeoAdmin
from django.http import HttpResponse
from django.urls import reverse
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


def linkify(field_name):
    """
    Converts a foreign key value into clickable links.

    If field_name is 'parent', link text will be str(obj.parent)
    Link will be admin url for the admin url for obj.parent.id:change
    """

    def _linkify(obj):
        linked_obj = getattr(obj, field_name)
        if linked_obj is None:
            return '-'
        app_label = linked_obj._meta.app_label
        model_name = linked_obj._meta.model_name
        view_name = f'admin:{app_label}_{model_name}_change'
        link_url = reverse(view_name, args=[linked_obj.pk])
        return format_html('<a href="{}">{}</a>', link_url, linked_obj)

    _linkify.short_description = field_name  # Sets column name
    return _linkify


@admin.display(description="country", ordering="country")
def country_flag(obj):
    _countries = None
    if hasattr(obj, "countries"):
        _countries = obj.countries
    elif hasattr(obj, "country"):
        _countries = obj.country
    if _countries is None:
        return ""
    if not isinstance(_countries, list):
        _countries = [_countries]
    return format_html(" ".join([f"<img src='{c.flag}'> {c.name}" for c in _countries]))


class BaseAdmin(OSMGeoAdmin):
    list_display = ["updated_on"]
    readonly_fields = ["created_on", "updated_on"]
    list_select_related = True
    actions = (export_model_display_as_csv, export_model_all_as_csv)


class BaseChoiceAdmin(admin.ModelAdmin):
    list_display = ["name"]
    ordering = ["name"]
    actions = (export_model_display_as_csv, export_model_all_as_csv)


@admin.register(Organization)
class OrganizationAdmin(BaseChoiceAdmin):
    pass


admin.site.unregister(UserModel)


class UserProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


@admin.register(UserModel)
class UserProfileAdmin(UserAdmin, BaseAdmin):
    readonly_fields = []
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
    def __init__(self, request, params, model, model_admin):
        self.title = "Country"
        if hasattr(model, "country"):
            self.parameter_name = "country"
        elif hasattr(model, "countries"):
            self.parameter_name = "countries"
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        countries = []
        for o in model_admin.model.objects.all():
            _countries = getattr(o, self.parameter_name)
            if not isinstance(_countries, list):
                _countries = [_countries]
            countries.extend(_countries)
        countries = set(countries)
        return [
            (c.code, format_html(f"<img src='{c.flag}'> {c.name}")) for c in countries
        ]

    def queryset(self, request, queryset):
        _field = getattr(queryset.model, self.parameter_name).field
        if self.value():
            if _field.multiple:
                return queryset.filter(country__icontains=self.value())
            return queryset.filter(country=self.value())
        else:
            return queryset


@admin.register(GovernanceType)
class GovernanceTypeAdmin(BaseChoiceAdmin):
    pass


@admin.register(ManagementAuthority)
class ManagementAuthorityAdmin(BaseChoiceAdmin):
    pass


@admin.register(ProtectedArea)
class ProtectedAreaAdmin(BaseChoiceAdmin):
    pass


@admin.register(Region)
class RegionAdmin(BaseChoiceAdmin):
    list_display = ["name", country_flag]
    list_filter = (CountryListFilter,)


@admin.register(StakeholderGroup)
class StakeholderGroupAdmin(BaseChoiceAdmin):
    pass


@admin.register(SupportSource)
class SupportSourceAdmin(BaseChoiceAdmin):
    pass


@admin.register(ManagementArea)
class ManagementAreaAdmin(BaseAdmin):
    list_display = ["pk", linkify(field_name="parent")] + BaseAdmin.list_display


class ManagementAreaZoneInline(admin.StackedInline):
    model = ManagementAreaZone
    extra = 0


@admin.register(ManagementAreaVersion)
class ManagementAreaVersionAdmin(BaseAdmin):
    list_display = [
        "name",
        "version_date",
        "governance_type",
        country_flag,
        "management_area",
    ] + BaseAdmin.list_display
    search_fields = ["name", "governance_type__name"]
    list_filter = ("governance_type", CountryListFilter, "management_area")
    # readonly_fields = ["management_area"] + BaseAdmin.readonly_fields
    filter_horizontal = ["regions", "stakeholder_groups", "support_sources"]
    inlines = [ManagementAreaZoneInline]


@admin.register(ManagementAreaZone)
class ManagementAreaZoneAdmin(BaseAdmin):
    list_display = ["name", "access_level"] + BaseAdmin.list_display
    search_fields = ["name"]
    list_filter = ("access_level",)

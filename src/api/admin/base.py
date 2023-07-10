import csv
import datetime
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.gis.admin import OSMGeoAdmin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin
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
            return "-"
        app_label = linked_obj._meta.app_label
        model_name = linked_obj._meta.model_name
        view_name = f"admin:{app_label}_{model_name}_change"
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
            return queryset.filter(country__iname=self.value())
        else:
            return queryset


@admin.register(AssessmentVersion)
class AssessmentVersionAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["year", "major_version", "updated_on"] + BaseAdmin.list_display


@admin.register(Attribute)
class AttributeAdmin(BaseChoiceAdmin, TranslationAdmin):
    list_display = ["name", "order", "required"]
    ordering = ["order", "name"]


@admin.register(Document)
class DocumentAdmin(BaseAdmin, TranslationAdmin):
    list_display = ["name", "version", "publication_date"] + BaseAdmin.list_display
    list_filter = ("version",)
    ordering = ["-version", "name"]


@admin.register(GovernanceType)
class GovernanceTypeAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(ManagementAuthority)
class ManagementAuthorityAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(Organization)
class OrganizationAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(ProtectedArea)
class ProtectedAreaAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(Region)
class RegionAdmin(BaseChoiceAdmin, TranslationAdmin):
    list_display = ["name", country_flag]
    list_filter = (CountryListFilter,)


@admin.register(StakeholderGroup)
class StakeholderGroupAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(SupportSource)
class SupportSourceAdmin(BaseChoiceAdmin, TranslationAdmin):
    pass


@admin.register(ActiveLanguage)
class ActiveLanguageAdmin(BaseAdmin):
    list_display = ["code", "name", "active"] + BaseAdmin.list_display
    readonly_fields = ["code", "name"] + BaseAdmin.readonly_fields

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync_languages/",
                self.admin_site.admin_view(self.sync_languages_view),
                name="sync_languages",
            )
        ]
        return custom_urls + urls

    def sync_languages_view(self, request):
        template = "admin/api/activelanguage/sync_languages.html"
        opts = self.model._meta
        context = dict(
            self.admin_site.each_context(request),
            opts=opts,
        )

        if request.method == "POST":
            existing_languages = [lang.code for lang in ActiveLanguage.objects.all()]
            results = []
            for language in settings.LANGUAGES:
                code = language[0]
                name = language[1]
                if code in existing_languages:
                    lang = ActiveLanguage.objects.get(code=code)
                    lang.name = name
                    lang.save()
                    results.append(f"Updated existing {code} with name {name}")
                    existing_languages.remove(code)
                else:
                    ActiveLanguage.objects.create(code=code, name=name)
                    results.append(f"Added new language {code} {name}")

            for code in existing_languages:
                lang = ActiveLanguage.objects.get(code=code)
                lang.delete()
                results.append(f"Deleted existing language {code}")

            for message in results:
                messages.success(request, message)

            return HttpResponseRedirect(reverse("admin:api_activelanguage_changelist"))

        return TemplateResponse(request, template, context)

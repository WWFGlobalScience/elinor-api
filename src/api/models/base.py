from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import connection
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

# from modeltranslation.utils import get_translation_fields


def latest_version():
    latest_version = AssessmentVersion.objects.order_by(
        "-year", "-major_version"
    ).first()
    return latest_version


class BaseModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_by",
    )
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by",
    )

    def validate_unique(self, exclude=None):
        # do normal uniqueness checks, using current language to check translated fields
        super().validate_unique(exclude)

        # repeat, using original non-translated fields
        errors = {}
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)
        for model_class, unique_check in unique_checks:
            # Query against everything, not filtered by translated field val
            qs = model_class._default_manager.all()
            model_class_pk = self._get_pk_val(model_class._meta)
            if not self._state.adding and model_class_pk is not None:
                qs = qs.exclude(pk=model_class_pk)

            lookup_kwargs = {}
            for field_name in unique_check:
                f = self._meta.get_field(field_name)
                lookup_value = getattr(self, f.attname)
                # TODO: Handle multiple backends with different feature flags.
                if lookup_value is None or (
                    lookup_value == ""
                    and connection.features.interprets_empty_strings_as_nulls
                ):
                    # no value, skip the lookup
                    continue
                if f.primary_key and not self._state.adding:
                    # no need to check for unique primary key when editing
                    continue
                lookup_kwargs[str(field_name)] = lookup_value

            # some fields were skipped, no reason to do the check
            if len(unique_check) != len(lookup_kwargs):
                continue

            if lookup_kwargs:
                for obj in qs:
                    obj_dict = {
                        k: v for k, v in obj.__dict__.items() if not k.startswith("_")
                    }
                    # check against original field
                    # TODO: check against all translated fields other than for the currently selected language?
                    # translated_field_names = get_translation_fields(field_name)
                    if all(
                        obj_dict.get(key) == value
                        for key, value in lookup_kwargs.items()
                    ):
                        if len(unique_check) == 1:
                            key = unique_check[0]
                        else:
                            key = NON_FIELD_ERRORS
                        errors.setdefault(key, []).append(
                            self.unique_error_message(model_class, unique_check)
                        )
                        continue

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class BaseChoiceModel(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Organization(BaseChoiceModel):
    pass


class Profile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    affiliation = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )
    accept_tor = models.BooleanField(default=False, verbose_name=_("accept ToR"))

    class Meta:
        verbose_name = _("user profile")

    def __str__(self):
        name = self.user.get_full_name()
        if name is None or name == "":
            name = self.user
        return f"{str(name)} {_('profile')}"


class GovernanceType(BaseChoiceModel):
    pass


class ManagementAuthority(BaseChoiceModel):
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "management authorities"


class ProtectedArea(BaseChoiceModel):
    pass


class Region(BaseChoiceModel):
    name = models.CharField(max_length=255)
    country = CountryField()

    class Meta:
        unique_together = ("name", "country")


class StakeholderGroup(BaseChoiceModel):
    pass


class SupportSource(BaseChoiceModel):
    pass


class AssessmentVersion(BaseModel):
    year = models.PositiveSmallIntegerField()
    major_version = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True)

    class Meta:
        ordering = ["year", "major_version"]

    def __str__(self):
        return f"{self.year}.{self.major_version}"


class Attribute(BaseChoiceModel):
    required = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "name"]


class Document(BaseModel):
    name = models.CharField(max_length=255)
    version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, default=latest_version
    )
    publication_date = models.DateField()
    file = models.FileField(upload_to="upload")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-version__year", "-version__major_version", "name"]

    def __str__(self):
        return f"{self.version} {self.name}"


class ActiveLanguage(BaseModel):
    code = models.CharField(unique=True, max_length=15)
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=False)

    class Meta:
        ordering = ["code", "name"]

    def __str__(self):
        return f"{self.code} {self.name}"

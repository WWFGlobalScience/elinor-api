from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from ..utils import update_assessment_version


DONTKNOW = 10
POOR = 20
AVERAGE = 30
GOOD = 40
EXCELLENT = 50
LIKERT_CHOICES = (
    (DONTKNOW, _(f"don't know [{DONTKNOW}]")),
    (POOR, _(f"poor [{POOR}]")),
    (AVERAGE, _(f"average [{AVERAGE}]")),
    (GOOD, _(f"good [{GOOD}]")),
    (EXCELLENT, _(f"excellent [{EXCELLENT}]")),
)


class AssessmentVersionMixin(models.Model):
    def save(self, *args, **kwargs):
        changed = False
        ignore_fields = ["created_on", "created_by", "updated_on", "updated_by"]
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        super().save(*args, **kwargs)

        if not old:  # new instance
            changed = True
        else:
            compare_fields = [
                f
                for f in self._meta.get_fields()
                if f.concrete and f.name not in ignore_fields
            ]
            for field in compare_fields:
                if getattr(old, field.name) != getattr(self, field.name):
                    changed = True
                    break

        if changed:
            update_assessment_version()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        update_assessment_version()

    class Meta:
        abstract = True


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

    class Meta:
        abstract = True


class BaseChoiceModel(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        abstract = True
        ordering = [
            "name",
        ]

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


class GovernanceType(BaseChoiceModel, AssessmentVersionMixin):
    pass


class ManagementAuthority(BaseChoiceModel):
    class Meta:
        ordering = [
            "name",
        ]
        verbose_name_plural = "management authorities"


class ProtectedArea(BaseChoiceModel):
    pass


class Region(BaseChoiceModel):
    name = models.CharField(max_length=255)
    country = CountryField()

    class Meta:
        unique_together = ("name", "country")


class StakeholderGroup(BaseChoiceModel, AssessmentVersionMixin):
    pass


class SupportSource(BaseChoiceModel, AssessmentVersionMixin):
    pass


class AssessmentVersion(BaseModel):
    year = models.PositiveSmallIntegerField()
    major_version = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["year", "major_version"]

    def __str__(self):
        return f"{self.year}.{self.major_version}"


class Attribute(BaseChoiceModel):
    required = models.BooleanField(default=True)

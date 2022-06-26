from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField


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


class Document(BaseModel):
    name = models.CharField(max_length=255)
    version = models.ForeignKey(AssessmentVersion, on_delete=models.PROTECT)
    publication_date = models.DateField()
    file = models.FileField(upload_to="upload")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-version__year", "-version__major_version", "name"]

    def __str__(self):
        return f"{self.version} {self.name}"

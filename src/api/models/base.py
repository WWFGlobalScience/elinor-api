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
    (DONTKNOW, _("don't know")),
    (POOR, _("poor")),
    (AVERAGE, _("average")),
    (GOOD, _("good")),
    (EXCELLENT, _("excellent")),
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
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Affiliation(BaseChoiceModel):
    pass


class Profile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    affiliation = models.ForeignKey(Affiliation, on_delete=models.SET_NULL, blank=True, null=True)
    contact_details = models.TextField(blank=True)
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


class ProtectedArea(BaseChoiceModel):
    pass


class Region(BaseChoiceModel):
    country = CountryField()


class ManagementAreaGroup(BaseModel):
    def __str__(self):
        return str(self.pk)


class ManagementArea(BaseModel):
    management_area_group = models.ForeignKey(
        ManagementAreaGroup, on_delete=models.PROTECT
    )
    name = models.CharField(max_length=255)
    date_established = models.DateField(null=True, blank=True)
    authority_name = models.CharField(max_length=255, blank=True)
    governance_type = models.ForeignKey(
        GovernanceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="governance_mas",
    )
    country = CountryField(multiple=True)
    region = models.ManyToManyField(Region, blank=True)
    polygon = models.MultiPolygonField(srid=4326, null=True, blank=True)
    # <= 1 billion ha; unrelated to actual geographic size
    reported_size = models.DecimalField(
        max_digits=11, decimal_places=2, null=True, blank=True
    )
    point = models.PointField(srid=4326, null=True, blank=True)
    import_file = models.FileField(upload_to="upload", blank=True, null=True)
    map_image = models.ImageField(upload_to="upload", blank=True, null=True)
    geospatial_sources = models.TextField(blank=True)

    class Meta:
        verbose_name = _("management area")
        ordering = ["name", "date_established"]

    def save(self, *args, **kwargs):
        if self.management_area_group_id is None:
            new_magroup = ManagementAreaGroup.objects.create()
            self.management_area_group = new_magroup
        super().save(*args, **kwargs)

    def __str__(self):
        _date = ""
        _country = ""
        if self.date_established:
            _date = f" [{self.date_established}]"
        if self.country:
            # noinspection PyTypeChecker
            _country = f" [{', '.join([c.name for c in self.country])}]"
        return f"{self.name}{_date}{_country}"


class ManagementAreaZone(BaseModel):
    OPEN_ACCESS = 90
    PARTIALLY_RESTRICTED = 50
    FULLY_RESTRICTED = 10
    ACCESS_CHOICES = (
        (OPEN_ACCESS, _("Open access (open for extraction and entering)")),
        (PARTIALLY_RESTRICTED, _("Fully restricted access (total extraction ban)")),
        (
            FULLY_RESTRICTED,
            _(
                "Partially Restricted (e.g., periodic closures, restriction by use type, restriction by "
                "activity type, species restrictions, gear restrictions, etc.)"
            ),
        ),
    )

    name = models.CharField(max_length=255)
    management_area = models.ForeignKey(
        ManagementArea, on_delete=models.CASCADE, related_name="ma_zones"
    )
    access_level = models.PositiveSmallIntegerField(
        choices=ACCESS_CHOICES, default=OPEN_ACCESS
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("management area zone")

    def __str__(self):
        return self.name

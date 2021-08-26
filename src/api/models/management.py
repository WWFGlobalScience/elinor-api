from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from .base import (
    BaseModel,
    GovernanceType,
    ManagementAuthority,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)
import datetime


class ManagementArea(BaseModel):
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return str(self.pk)


class ManagementAreaVersion(BaseModel):
    LOCAL = "local"
    NATIONAL = "national"
    INTERNATIONAL = "international"
    RECOGNITION_TYPES = (
        (LOCAL, _(LOCAL)),
        (NATIONAL, _(NATIONAL)),
        (INTERNATIONAL, _(INTERNATIONAL)),
    )

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

    management_area = models.ForeignKey(ManagementArea, on_delete=models.PROTECT)
    name = models.CharField(blank=True, null=True, max_length=255)
    protected_area = models.ForeignKey(
        ProtectedArea, on_delete=models.SET_NULL, blank=True, null=True
    )
    date_established = models.DateField(null=True, blank=True)
    version_date = models.DateField(default=datetime.date.today)
    management_authority = models.ForeignKey(
        ManagementAuthority, on_delete=models.SET_NULL, blank=True, null=True
    )
    recognition_level = models.CharField(
        max_length=100, choices=RECOGNITION_TYPES, blank=True, null=True
    )
    stakeholder_groups = models.ManyToManyField(StakeholderGroup, blank=True)
    support_sources = models.ManyToManyField(SupportSource, blank=True)
    governance_type = models.ForeignKey(
        GovernanceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="governance_mas",
    )
    countries = CountryField(multiple=True)
    regions = models.ManyToManyField(Region, blank=True)
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
        verbose_name = _("management area version")
        ordering = ["name", "date_established"]

    def __str__(self):
        _countries = ""
        if self.countries:
            # noinspection PyTypeChecker
            _countries = f" [{', '.join([c.name for c in self.countries])}]"
        return f"{self.name} [{self.version_date}]{_countries}"


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
    management_area_version = models.ForeignKey(
        ManagementAreaVersion, on_delete=models.CASCADE, related_name="ma_zones"
    )
    access_level = models.PositiveSmallIntegerField(
        choices=ACCESS_CHOICES, default=OPEN_ACCESS
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("management area zone")

    def __str__(self):
        return self.name

import datetime
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
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
from ..utils.management import get_multipolygon_from_import_file


class ManagementArea(BaseModel):
    _polygon_from_file = None
    assessment_lookup = "assessment"

    LOCAL = "local"
    NATIONAL = "national"
    INTERNATIONAL = "international"
    RECOGNITION_TYPES = (
        (LOCAL, _(LOCAL)),
        (NATIONAL, _(NATIONAL)),
        (INTERNATIONAL, _(INTERNATIONAL)),
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="versions",
    )
    # just a FK; for actual spatial query use polygon intersection
    containedby = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="mas_inside",
    )
    name = models.CharField(max_length=255)
    protected_area = models.ForeignKey(
        ProtectedArea, on_delete=models.SET_NULL, blank=True, null=True
    )
    wdpa_protected_area = models.IntegerField(
        null=True, blank=True, verbose_name="WDPA ID"
    )
    date_established = models.DateField(null=True, blank=True)
    version_date = models.DateField(default=datetime.date.today)
    management_authority = models.ForeignKey(
        ManagementAuthority, on_delete=models.SET_NULL, blank=True, null=True
    )
    recognition_level = ArrayField(
        models.TextField(choices=RECOGNITION_TYPES), blank=True
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
    countries = CountryField(multiple=True, blank=True)
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
    objectives = models.TextField(blank=True)

    def clean(self):
        if self.import_file._committed is False:
            self._polygon_from_file = get_multipolygon_from_import_file(
                self.import_file
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self._polygon_from_file:
            self.polygon = self._polygon_from_file.geos
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("management area")
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

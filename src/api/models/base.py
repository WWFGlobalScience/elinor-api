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


class Profile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    affiliation = models.CharField(max_length=255)
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


class Region(BaseChoiceModel):
    country = CountryField()


class ManagementArea(BaseModel):
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
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="region_mas",
    )
    polygon = models.PolygonField(srid=4326, null=True, blank=True)
    # <= 1 billion ha; unrelated to actual geographic size
    reported_size = models.DecimalField(
        max_digits=11, decimal_places=2, null=True, blank=True
    )
    point = models.PointField(srid=4326, null=True, blank=True)
    map_image = models.ImageField(blank=True, null=True)

    class Meta:
        verbose_name = _("management area")
        ordering = ["name", "date_established"]

    def __str__(self):
        _date = ""
        _country = ""
        if self.date_established:
            _date = f" [{self.date_established}]"
        if self.country:
            _country = f" [{', '.join([c.name for c in self.country])}]"
        return f"{self.name}{_date}{_country}"


class ManagementAreaZone(BaseModel):
    name = models.CharField(max_length=255)
    management_area = models.ForeignKey(
        ManagementArea, on_delete=models.CASCADE, related_name="ma_zones"
    )
    restricted = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("management area zone")

    def __str__(self):
        return self.name

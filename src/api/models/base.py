from django.conf import settings
from django.contrib.gis.db import models
from django_countries.fields import CountryField


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
    accept_tor = models.BooleanField(default=False, verbose_name="accept ToR")

    class Meta:
        verbose_name = "user profile"

    def __str__(self):
        name = self.user.get_full_name()
        if name is None or name == "":
            name = self.user
        return f"{str(name)} profile"


class GovernanceType(BaseChoiceModel):
    pass


class Region(BaseChoiceModel):
    country = CountryField()


class ManagementArea(BaseModel):
    name = models.CharField(max_length=255)
    date_established = models.DateField(null=True, blank=True)
    governance_type = models.ForeignKey(
        GovernanceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="governance_mas",
    )
    country = CountryField(null=True, blank=True)
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="region_mas",
    )
    polygon = models.PolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["name", "date_established"]

    def __str__(self):
        _date = ""
        _country = ""
        if self.date_established:
            _date = f" [{self.date_established}]"
        if self.country:
            _country = f" [{self.country}]"
        return f"{self.name}{_date}{_country}"

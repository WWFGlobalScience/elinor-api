from django.contrib.gis.db import models
from .base import BaseModel, ManagementArea


class Assessment(BaseModel):
    name = models.CharField(max_length=255)
    management_area = models.ForeignKey(
        ManagementArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ma_assessments",
    )
    count_manager = models.PositiveSmallIntegerField(
        default=0, verbose_name="MA manager count"
    )
    count_personnel = models.PositiveSmallIntegerField(
        default=0, verbose_name="MA personnel count"
    )
    count_government = models.PositiveSmallIntegerField(
        default=0, verbose_name="government personnel count"
    )
    count_committee = models.PositiveSmallIntegerField(
        default=0, verbose_name="local community/indigenous committee count"
    )
    count_community = models.PositiveSmallIntegerField(
        default=0, verbose_name="community leader count"
    )
    focal_area = models.TextField(blank=True)

    def __str__(self):
        return self.name

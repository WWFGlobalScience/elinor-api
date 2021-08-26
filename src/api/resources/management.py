from django_countries.serializers import CountryFieldMixin
from django_filters import (
    DateFromToRangeFilter,
    RangeFilter,
)
from rest_framework_gis.filters import GeometryFilter
from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
    GovernanceType,
    ManagementAuthority,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)
from ..models.management import (
    ManagementArea,
    ManagementAreaVersion,
    ManagementAreaZone,
)
from ..permissions import (
    ReadOnlyOrAuthenticatedCreate,
    ReadOnlyOrAuthenticatedCreateOrOwner,
)

from rest_framework import serializers

class ManagementAreaSerializer(BaseAPISerializer):
    class Meta:
        model = ManagementArea
        exclude = []


class ManagementAreaFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ManagementArea
        exclude = []


class ManagementAreaViewSet(BaseAPIViewSet):
    queryset = ManagementArea.objects.all()
    ordering = ["pk"]
    serializer_class = ManagementAreaSerializer
    filter_class = ManagementAreaFilterSet
    permission_classes = [
        ReadOnlyOrAuthenticatedCreate,
    ]

class ManagementAreaVersionStakeholderGroupSerializer(BaseAPISerializer):
    class Meta:
        model = StakeholderGroup
        fields = ["id", "name"]

class ManagementAreaVersionSupportSourceSerializer(BaseAPISerializer):
    class Meta:
        model = SupportSource
        fields = ["id", "name"]

class ManagementAreaVersionProtectedAreaSerializer(BaseAPISerializer):
    class Meta:
        model = ProtectedArea
        fields = ["id", "name"]

class ManagementAreaVersionGovernanceTypeSerializer(BaseAPISerializer):
    class Meta:
        model = GovernanceType
        fields = ["id", "name"]

class ManagementAreaVersionRegionSerializer(BaseAPISerializer):
    class Meta:
        model = Region
        fields = ["id", "name"]

class ManagementAreaVersionManagementAuthoritySerializer(BaseAPISerializer):
    class Meta:
        model = ManagementAuthority
        fields = ["id", "name"]

class ManagementAreaVersionSerializer(CountryFieldMixin, BaseAPISerializer):
    stakeholder_groups = ManagementAreaVersionStakeholderGroupSerializer(many=True)
    support_sources = ManagementAreaVersionSupportSourceSerializer(many=True)
    protected_area = ManagementAreaVersionProtectedAreaSerializer(many=False)
    governance_type = ManagementAreaVersionGovernanceTypeSerializer(many=False)
    regions = ManagementAreaVersionRegionSerializer(many=True)
    management_authority = ManagementAreaVersionManagementAuthoritySerializer(many=False)
    class Meta:
        model = ManagementAreaVersion
        exclude = []

class ManagementAreaVersionFilterSet(BaseAPIFilterSet):
    date_established = DateFromToRangeFilter()
    version_date = DateFromToRangeFilter()
    reported_size = RangeFilter()
    intersects_polygon = GeometryFilter(field_name="polygon", lookup_expr="intersects")

    class Meta:
        model = ManagementAreaVersion
        exclude = ["geospatial_sources", "import_file", "map_image", "polygon", "point"]


class ManagementAreaVersionViewSet(BaseAPIViewSet):
    queryset = ManagementAreaVersion.objects.all()
    ordering = ["name", "version_date"]
    serializer_class = ManagementAreaVersionSerializer
    filter_class = ManagementAreaVersionFilterSet
    search_fields = ["name", "protected_area__name", "management_authority__name"]
    permission_classes = [
        ReadOnlyOrAuthenticatedCreateOrOwner,
    ]


class ManagementAreaZoneSerializer(BaseAPISerializer):
    class Meta:
        model = ManagementAreaZone
        exclude = []


class ManagementAreaZoneFilterSet(BaseAPIFilterSet):
    class Meta:
        model = ManagementAreaZone
        exclude = ["description"]


class ManagementAreaZoneViewSet(BaseAPIViewSet):
    queryset = ManagementAreaZone.objects.all()
    ordering = ["name", "management_area_version"]
    serializer_class = ManagementAreaZoneSerializer
    filter_class = ManagementAreaZoneFilterSet
    search_fields = ["name", "management_area_version__name"]
    permission_classes = [
        ReadOnlyOrAuthenticatedCreateOrOwner,
    ]

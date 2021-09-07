from django_countries.serializers import CountryFieldMixin
from django_filters import (
    CharFilter,
    DateFromToRangeFilter,
    RangeFilter,
)
from rest_framework_gis.filters import GeometryFilter
from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
    PrimaryKeyExpandedField,
    ReadOnlyChoiceSerializer,
)
from ..models import (
    GovernanceType,
    ManagementArea,
    ManagementAreaZone,
    ManagementAuthority,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)
from ..permissions import AssessmentReadOnlyOrAuthenticatedUserPermission


class ManagementAreaSerializer(CountryFieldMixin, BaseAPISerializer):
    stakeholder_groups = PrimaryKeyExpandedField(
        queryset=StakeholderGroup.objects.all(),
        many=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    support_sources = PrimaryKeyExpandedField(
        queryset=SupportSource.objects.all(),
        many=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    protected_area = PrimaryKeyExpandedField(
        queryset=ProtectedArea.objects.all(),
        allow_null=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    governance_type = PrimaryKeyExpandedField(
        queryset=GovernanceType.objects.all(),
        allow_null=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    regions = PrimaryKeyExpandedField(
        queryset=Region.objects.all(),
        many=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    management_authority = PrimaryKeyExpandedField(
        queryset=ManagementAuthority.objects.all(),
        allow_null=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )

    class Meta:
        model = ManagementArea
        exclude = []


class ManagementAreaFilterSet(BaseAPIFilterSet):
    date_established = DateFromToRangeFilter()
    version_date = DateFromToRangeFilter()
    reported_size = RangeFilter()
    intersects_polygon = GeometryFilter(field_name="polygon", lookup_expr="intersects")
    recognition_level = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ManagementArea
        exclude = ["geospatial_sources", "import_file", "map_image", "polygon", "point"]


class ManagementAreaViewSet(BaseAPIViewSet):
    queryset = ManagementArea.objects.all()
    ordering = ["name", "version_date"]
    serializer_class = ManagementAreaSerializer
    filter_class = ManagementAreaFilterSet
    search_fields = ["name", "protected_area__name", "management_authority__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]


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
    ordering = ["name", "management_area__name"]
    serializer_class = ManagementAreaZoneSerializer
    filter_class = ManagementAreaZoneFilterSet
    search_fields = ["name", "management_area__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

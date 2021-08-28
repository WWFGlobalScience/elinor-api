from django_countries.serializers import CountryFieldMixin
from django_filters import (
    DateFromToRangeFilter,
    RangeFilter,
)
from rest_framework import serializers
from rest_framework_gis.filters import GeometryFilter
from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
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
    stakeholder_group_ids = serializers.PrimaryKeyRelatedField(
        queryset=StakeholderGroup.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )
    stakeholder_groups = ReadOnlyChoiceSerializer(many=True, read_only=True)
    support_source_ids = serializers.PrimaryKeyRelatedField(
        queryset=SupportSource.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )
    support_sources = ReadOnlyChoiceSerializer(many=True, read_only=True)
    protected_area_id = serializers.PrimaryKeyRelatedField(
        queryset=ProtectedArea.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    protected_area = ReadOnlyChoiceSerializer(read_only=True)
    governance_type_id = serializers.PrimaryKeyRelatedField(
        queryset=GovernanceType.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    governance_type = ReadOnlyChoiceSerializer(read_only=True)
    region_ids = serializers.PrimaryKeyRelatedField(
        queryset=StakeholderGroup.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )
    regions = ReadOnlyChoiceSerializer(many=True, read_only=True)
    management_authority_id = serializers.PrimaryKeyRelatedField(
        queryset=ManagementAuthority.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    management_authority = ReadOnlyChoiceSerializer(read_only=True)

    class Meta:
        model = ManagementArea
        exclude = []


class ManagementAreaFilterSet(BaseAPIFilterSet):
    date_established = DateFromToRangeFilter()
    version_date = DateFromToRangeFilter()
    reported_size = RangeFilter()
    intersects_polygon = GeometryFilter(field_name="polygon", lookup_expr="intersects")

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

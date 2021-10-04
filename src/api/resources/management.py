import itertools
from django_countries.fields import Country
from django_countries.serializers import CountryFieldMixin
from django_filters import (
    CharFilter,
    ChoiceFilter,
    DateFromToRangeFilter,
    RangeFilter,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_gis.filters import GeometryFilter
from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
    PrimaryKeyExpandedField,
    ReadOnlyChoiceSerializer,
)
from ..models import (
    Assessment,
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
    containedby = PrimaryKeyExpandedField(
        queryset=ManagementArea.objects.all(),
        allow_null=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )

    def save(self, **kwargs):
        if "countries" in self.validated_data:
            countries = self.validated_data["countries"]
            unique_countries = list(set(countries))
            self.validated_data["countries"] = unique_countries
        return super().save(**kwargs)

    class Meta:
        model = ManagementArea
        exclude = []


class ManagementAreaFilterSet(BaseAPIFilterSet):
    date_established = DateFromToRangeFilter()
    version_date = DateFromToRangeFilter()
    reported_size = RangeFilter()
    intersects_polygon = GeometryFilter(field_name="polygon", lookup_expr="intersects")
    recognition_level = CharFilter(lookup_expr="icontains")
    assessment_data_policy = ChoiceFilter(
        choices=Assessment.DATA_POLICIES,
        field_name="assessment__data_policy",
    )

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

    @action(methods=["GET"], detail=False)
    def countries(self, request):
        chosen_countries_qs = self.get_queryset().values_list("countries")
        chosen_countries = [c[0].split(",") for c in chosen_countries_qs]
        chosen_countries_flattened = list(
            itertools.chain.from_iterable(chosen_countries)
        )
        unique_chosen_countries = [
            Country(c) for c in list(set(chosen_countries_flattened))
        ]
        response = [
            {"code": c.code, "name": c.name, "flag": c.flag}
            for c in unique_chosen_countries
        ]

        return Response(response)


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

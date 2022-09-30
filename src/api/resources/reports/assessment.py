from django.conf import settings
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from . import BaseReportSerializer, ReportView
from ..assessment import get_assessment_related_queryset
from ...models import Assessment, ManagementArea, SurveyAnswerLikert
from ...permissions import AssessmentReadOnlyOrAuthenticatedUserPermission


class SurveyAnswerLikertSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()

    def get_question(self, obj):
        return obj.question.key

    class Meta:
        model = SurveyAnswerLikert
        fields = ["question", "choice", "explanation"]


# TODO: deal with ManagementAreaZone, parent/containedby
class ManagementAreaReportSerializer(CountryFieldMixin, BaseReportSerializer):
    protected_area = serializers.StringRelatedField()
    management_authority = serializers.StringRelatedField()
    stakeholder_groups = serializers.StringRelatedField(many=True)
    support_sources = serializers.StringRelatedField(many=True)
    governance_type = serializers.StringRelatedField()
    countries = serializers.SerializerMethodField()
    regions = serializers.StringRelatedField(many=True)

    def get_countries(self, obj):
        return [c.name for c in obj.countries]

    class Meta:
        model = ManagementArea
        fields = [
            "id",
            "created_on",
            "created_by",
            "updated_on",
            "updated_by",
            "name",
            "protected_area",
            "wdpa_protected_area",
            "date_established",
            "version_date",
            "management_authority",
            "recognition_level",
            "stakeholder_groups",
            "support_sources",
            "governance_type",
            "countries",
            "regions",
            "reported_size",
            "geospatial_sources",
            "objectives",
        ]


class AssessmentReportSerializer(BaseReportSerializer):
    published_version = serializers.StringRelatedField()
    organization = serializers.StringRelatedField()
    status = serializers.CharField(source="get_status_display")
    data_policy = serializers.CharField(source="get_data_policy_display")
    attributes = serializers.StringRelatedField(many=True)
    person_responsible = serializers.CharField(
        source="person_responsible.get_full_name"
    )
    person_responsible_role = serializers.CharField(
        source="get_person_responsible_role_display"
    )
    collection_method = serializers.CharField(source="get_collection_method_display")
    management_area = ManagementAreaReportSerializer()
    survey_answer_likerts = serializers.SerializerMethodField()

    def get_survey_answer_likerts(self, obj):
        answer_likerts = obj.survey_answer_likerts.all().order_by(
            "question__attribute__order", "question__number"
        )
        return SurveyAnswerLikertSerializer(answer_likerts, many=True).data

    class Meta:
        model = Assessment
        fields = [
            "id",
            "created_on",
            "created_by",
            "updated_on",
            "updated_by",
            "published_version",
            "name",
            "organization",
            "status",
            "data_policy",
            "attributes",
            "person_responsible",
            "person_responsible_role",
            "person_responsible_role_other",
            "year",
            "count_community",
            "count_ngo",
            "count_academic",
            "count_government",
            "count_private",
            "count_indigenous",
            "consent_given",
            "consent_given_written",
            "management_plan_file",
            "collection_method",
            "collection_method_text",
            "management_area",
            "survey_answer_likerts",
        ]


class AssessmentReportGeoSerializer(
    GeoFeatureModelSerializer, AssessmentReportSerializer
):
    polygon = GeometryField(
        source="management_area.polygon", precision=settings.GEO_PRECISION
    )

    class Meta(AssessmentReportSerializer.Meta):
        geo_field = "polygon"


class AssessmentReportView(ReportView):
    ordering = ["name", "year"]
    serializer_class = AssessmentReportSerializer
    serializer_class_geojson = AssessmentReportGeoSerializer
    # TODO: add filters and search
    # filter_class = AssessmentFilterSet
    # search_fields = ["name", "management_area__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

    # TODO: optimize all report queries
    def get_queryset(self):
        return (
            get_assessment_related_queryset(self.request.user, Assessment)
            .select_related("management_area", "management_area__protected_area")
            .prefetch_related("assessment_flags")
        )

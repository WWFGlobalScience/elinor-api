from django.conf import settings
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from . import BaseReportSerializer, ReportView
from ..assessment import get_assessment_related_queryset
from ...models import (
    Assessment,
    ManagementArea,
    SurveyAnswerLikert,
    SurveyQuestionLikert,
)
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
    survey_answer_likerts = SurveyAnswerLikertSerializer(many=True)

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
            "count_gender_female",
            "count_gender_male",
            "count_gender_nonbinary",
            "count_gender_prefer_not_say",
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
        source="management_area.polygon", precision=settings.GEO_PRECISION, default=None
    )

    class Meta(AssessmentReportSerializer.Meta):
        geo_field = "polygon"


class AssessmentReportView(ReportView):
    ordering = ["name", "year"]
    serializer_class = AssessmentReportSerializer
    serializer_class_geojson = AssessmentReportGeoSerializer
    csv_method_fields = ["survey_answer_likerts"]
    file_prefix = "assessmentreport"
    _question_likerts = None
    # TODO: add filters and search
    # filter_class = AssessmentFilterSet
    # search_fields = ["name", "management_area__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

    def get_queryset(self):
        return (
            get_assessment_related_queryset(self.request.user, Assessment)
            .select_related("management_area", "management_area__protected_area")
            .prefetch_related("assessment_flags")
        )

    @property
    def question_likerts(self):
        if not self._question_likerts:
            questions = SurveyQuestionLikert.objects.order_by(
                "attribute__order", "number"
            )
            self._question_likerts = questions
        return self._question_likerts

    def get_answer_by_slug(self, answers, slug):
        if answers:
            for answer in answers:
                if answer["question"] == slug:
                    return answer
        return None

    def get_survey_answer_likerts(self, obj=None):
        answers = []
        for question in self.question_likerts:
            choice_name = f"{question.key}__choice"
            explanation_name = f"{question.key}__explanation"
            choice_field = {choice_name: None}
            explanation_field = {explanation_name: None}

            answer = self.get_answer_by_slug(obj, question.key)
            if answer:
                choice_field[choice_name] = answer.get("choice")
                explanation_field[explanation_name] = answer.get("explanation")

            answers.append(choice_field)
            answers.append(explanation_field)

        return answers

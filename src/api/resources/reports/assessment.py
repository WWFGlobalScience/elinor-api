from collections import defaultdict
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
from ...models.base import EXCELLENT
from ...permissions import AssessmentReadOnlyOrAuthenticatedUserPermission
from ...utils import slugify


ATTRIBUTE_NORMALIZER = 10


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
    person_responsible = serializers.CharField(
        source="person_responsible.get_full_name"
    )
    person_responsible_role = serializers.CharField(
        source="get_person_responsible_role_display"
    )
    collection_method = serializers.CharField(source="get_collection_method_display")
    management_area = ManagementAreaReportSerializer()
    attributes = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    def attribute_scores(self, obj):
        answers = (
            SurveyAnswerLikert.objects.filter(assessment=obj)
            .select_related("question", "question__attribute")
            .order_by(
                "question__attribute__order",
                "question__attribute__name",
                "question__number",
            )
        )

        attributes = defaultdict(list)
        for a in answers:
            answer = {
                "question": a.question.key,
                "choice": a.choice,
                "explanation": a.explanation,
            }
            attributes[a.question.attribute.name].append(answer)

        output_attributes = []
        for attrib, answers in attributes.items():
            nonnullanswers = [a for a in answers if a["choice"] is not None]
            total_points = len(nonnullanswers) * EXCELLENT
            points = sum([a["choice"] for a in nonnullanswers])
            score = points / total_points
            normalized_score = round(score * ATTRIBUTE_NORMALIZER, 1)
            output_attributes.append(
                {"attribute": attrib, "score": normalized_score, "answers": answers}
            )

        return output_attributes

    def get_attributes(self, obj):
        output_attributes = self.attribute_scores(obj)
        return output_attributes

    def get_score(self, obj):
        attributes = self.attribute_scores(obj)
        attributes_count = len(attributes)
        if attributes_count == 0:
            attributes_count = 1
        total_attribs = attributes_count * ATTRIBUTE_NORMALIZER
        scores_total = sum([a["score"] for a in attributes])
        score_ratio = scores_total / total_attribs
        normalized_score = round(score_ratio * 100)
        return normalized_score

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
            "strengths_explanation",
            "needs_explanation",
            "context",
            "management_area",
            "attributes",
            "score",
        ]


class AssessmentReportGeoSerializer(
    GeoFeatureModelSerializer, AssessmentReportSerializer
):
    polygon = GeometryField(
        source="management_area.polygon", precision=settings.GEO_PRECISION, default=None
    )

    class Meta(AssessmentReportSerializer.Meta):
        geo_field = "polygon"
        fields = AssessmentReportSerializer.Meta.fields + ["polygon"]


class AssessmentReportView(ReportView):
    ordering = ["name", "year"]
    serializer_class = AssessmentReportSerializer
    serializer_class_geojson = AssessmentReportGeoSerializer
    csv_method_fields = ["attributes"]
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

    def get_attributes(self, obj=None):
        csv_fields = []
        attribute = None
        for question in self.question_likerts:
            attrib_field = attrib_name = None
            if attribute != question.attribute:
                attribute = question.attribute
                attrib_name = f"{slugify(attribute.name)}__score"
                attrib_field = {attrib_name: None}
                csv_fields.append(attrib_field)

            choice_name = f"{question.key}__choice"
            explanation_name = f"{question.key}__explanation"
            choice_field = {choice_name: None}
            explanation_field = {explanation_name: None}

            answer = self.get_answer_by_slug(obj, attribute.name, question.key)
            if answer:
                if attrib_field and attrib_name:
                    attrib_field[attrib_name] = answer.get("score")
                choice_field[choice_name] = answer.get("choice")
                explanation_field[explanation_name] = answer.get("explanation")

            csv_fields.append(choice_field)
            csv_fields.append(explanation_field)

        return csv_fields

    @property
    def question_likerts(self):
        if not self._question_likerts:
            questions = SurveyQuestionLikert.objects.select_related(
                "attribute"
            ).order_by("attribute__order", "attribute__name", "number")
            self._question_likerts = questions
        return self._question_likerts

    def get_answer_by_slug(self, attributes, attrib_name, slug):
        if attributes:
            for attribute in attributes:
                for answer in attribute["answers"]:
                    if answer["question"] == slug:
                        return {
                            "score": attribute["score"],
                            "choice": answer["choice"],
                            "explanation": answer["explanation"],
                        }
        return None

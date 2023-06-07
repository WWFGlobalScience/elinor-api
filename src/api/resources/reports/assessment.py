from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from django_filters import ChoiceFilter
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField, GeometrySerializerMethodField
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from . import BaseReportSerializer, ReportView
from ..assessment import get_assessment_related_queryset
from ..base import BaseAPIFilterSet
from ...models import (
    Assessment,
    ManagementArea,
    SurveyQuestionLikert,
)
from ...permissions import AssessmentReadOnlyOrAuthenticatedUserPermission
from ...utils import slugify
from ...utils.assessment import attribute_scores, assessment_score


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attribute_scores = None

    def get_attribute_scores(self, obj):
        if self._attribute_scores is None:
            self._attribute_scores = attribute_scores(obj)
        return self._attribute_scores

    def get_attributes(self, obj):
        return self.get_attribute_scores(obj)

    def get_score(self, obj):
        return assessment_score(self.get_attribute_scores(obj))

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
    geom = GeometrySerializerMethodField()

    def get_geom(self, obj):
        polygon = obj.management_area.polygon
        point = obj.management_area.point
        geomfield = GeometryField(precision=settings.GEO_PRECISION, default=None)

        geom = None
        if polygon:
            geom = polygon
        elif point:
            geom = point

        if geom:
            geomfield_value = GEOSGeometry(geom.wkt)
            processed_geom_geojson = geomfield.to_representation(geomfield_value)
            return GEOSGeometry(str(processed_geom_geojson))

        return None

    class Meta(AssessmentReportSerializer.Meta):
        geo_field = "geom"
        fields = AssessmentReportSerializer.Meta.fields


class AssessmentReportFilterSet(BaseAPIFilterSet):
    # Same as resources/assessments/AssessmentFilterSet
    management_area_countries = ChoiceFilter(
        field_name="management_area__countries",
        choices=countries,
        lookup_expr="icontains",
    )

    class Meta:
        model = Assessment
        exclude = ["management_plan_file"]


class AssessmentReportView(ReportView):
    ordering = ["name", "year"]
    serializer_class = AssessmentReportSerializer
    serializer_class_geojson = AssessmentReportGeoSerializer
    csv_method_fields = ["attributes"]
    file_prefix = "assessmentreport"
    _question_likerts = None
    filter_class = AssessmentReportFilterSet
    search_fields = ["name", "management_area__name"]
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

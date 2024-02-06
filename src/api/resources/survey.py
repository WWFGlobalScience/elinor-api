from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseAPIViewSet,
    PrimaryKeyExpandedField,
    ReadOnlyChoiceSerializer,
)
from ..models import Assessment, SurveyAnswerLikert, SurveyQuestionLikert
from ..permissions import AssessmentReadOnlyOrAuthenticatedUserPermission, ReadOnly
from ..utils.assessment import get_assessment_related_queryset


class SurveyQuestionLikertSerializer(BaseAPISerializer):
    class Meta:
        model = SurveyQuestionLikert
        exclude = []


class SurveyQuestionLikertFilterSet(BaseAPIFilterSet):
    class Meta:
        model = SurveyQuestionLikert
        exclude = []


class SurveyQuestionLikertViewSet(BaseAPIViewSet):
    serializer_class = SurveyQuestionLikertSerializer
    filter_class = SurveyQuestionLikertFilterSet
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return SurveyQuestionLikert.objects.all()


class SurveyAnswerLikertSerializer(BaseAPISerializer):
    assessment = PrimaryKeyExpandedField(
        queryset=Assessment.objects.all(),
        serializer=ReadOnlyChoiceSerializer,
    )
    question = PrimaryKeyExpandedField(
        queryset=SurveyQuestionLikert.objects.all(),
        serializer=SurveyQuestionLikertSerializer,
    )

    class Meta:
        model = SurveyAnswerLikert
        exclude = []


class SurveyAnswerLikertFilterSet(BaseAPIFilterSet):
    class Meta:
        model = SurveyAnswerLikert
        exclude = []


class SurveyAnswerLikertViewSet(BaseAPIViewSet):
    ordering = ["assessment", "question"]
    serializer_class = SurveyAnswerLikertSerializer
    filter_class = SurveyAnswerLikertFilterSet
    search_fields = ["assessment__name", "question__key", "question__attribute__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, SurveyAnswerLikert)

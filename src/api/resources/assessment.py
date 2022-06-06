from django.db.models import Q
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from django_filters import (
    ChoiceFilter,
    DateTimeFromToRangeFilter,
    ModelChoiceFilter,
    NumberFilter,
)
from rest_framework import serializers
from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
    user_choice_qs,
    PrimaryKeyExpandedField,
    ReadOnlyChoiceSerializer,
    UserSerializer,
)
from ..models import (
    Assessment,
    AssessmentChange,
    Attribute,
    Collaborator,
    ManagementArea,
    Organization,
    SurveyQuestionLikert,
    SurveyAnswerLikert,
)
from ..permissions import (
    ReadOnly,
    AssessmentReadOnlyOrAuthenticatedUserPermission,
    CollaboratorReadOnlyOrAuthenticatedUserPermission,
)
from ..utils.assessment import enforce_required_attributes, log_assessment_change


def get_assessment_related_queryset(user, model):
    lookup = model.assessment_lookup
    if lookup != "":
        lookup = f"{lookup}__"
    qs = model.objects.all()
    qry = Q(**{f"{lookup}status__lte": Assessment.PUBLISHED}) & Q(
        **{f"{lookup}data_policy__gte": Assessment.PUBLIC}
    )
    if user.is_authenticated:
        qs = model.objects.prefetch_related(f"{lookup}collaborators")
        qry |= Q(**{f"{lookup}collaborators__user": user})
    return qs.filter(qry).distinct()


class AssessmentCollaboratorSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Collaborator
        fields = ["id", "user", "role"]


class AssessmentMASerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = ManagementArea
        fields = ["id", "countries"]


class AssessmentSerializer(BaseAPISerializer):
    person_responsible = PrimaryKeyExpandedField(
        queryset=user_choice_qs,
        default=serializers.CurrentUserDefault(),
        serializer=UserSerializer,
    )
    organization = PrimaryKeyExpandedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
        serializer=ReadOnlyChoiceSerializer,
    )
    collaborators = AssessmentCollaboratorSerializer(many=True, read_only=True)
    management_area_countries = AssessmentMASerializer(
        read_only=True, source="management_area"
    )
    published_version = serializers.StringRelatedField(read_only=True)

    # def validate(self, data):
    #     required_attributes = Attribute.objects.filter(required=True)
    #     _attributes = []
    #     if self.instance:  # existing attributes, if any
    #         _attributes = self.instance.attributes.all()
    #     if data and "attributes" in data:  # proposed new attributes, if any
    #         _attributes = data["attributes"]
    #     missing_required = [str(ra) for ra in required_attributes if ra not in _attributes]
    #
    #     if missing_required:
    #         msg = f"May not save without including required attributes: {', '.join(missing_required)}"
    #         raise serializers.ValidationError({"attributes": _(msg)})
    #
    #     return data

    class Meta:
        model = Assessment
        exclude = []


class AssessmentFilterSet(BaseAPIFilterSet):
    person_responsible = ModelChoiceFilter(queryset=user_choice_qs)
    # actual management_area__countries field is varchar like "US,AX,ES"
    # Filter depends on lookup_expr="icontains" with field storing unique 2-character country codes
    management_area_countries = ChoiceFilter(
        field_name="management_area__countries",
        choices=countries,
        lookup_expr="icontains",
    )
    collaborators = NumberFilter(field_name="collaborators__user", distinct=True)

    class Meta:
        model = Assessment
        exclude = ["management_plan_file"]


class AssessmentViewSet(BaseAPIViewSet):
    ordering = ["name", "year"]
    serializer_class = AssessmentSerializer
    filter_class = AssessmentFilterSet
    search_fields = ["name", "management_area__name"]
    permission_classes = [
        AssessmentReadOnlyOrAuthenticatedUserPermission,
    ]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, Assessment)

    def perform_create(self, serializer):
        user = self.request.user
        assessment = serializer.save()
        enforce_required_attributes(assessment)
        Collaborator.objects.create(
            assessment=assessment, user=user, role=Collaborator.ADMIN
        )

    def perform_update(self, serializer):
        user = self.request.user
        original_assessment = self.get_object()
        edited_assessment = serializer.save()
        enforce_required_attributes(edited_assessment)
        log_assessment_change(original_assessment, edited_assessment, user)


class AssessmentChangeSerializer(BaseAPISerializer):
    event_type = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentChange
        exclude = []

    # noinspection PyMethodMayBeStatic
    def get_event_type(self, obj):
        if obj.event_type is None:
            return None
        event_types = {t[0]: t[1] for t in AssessmentChange.EVENT_TYPES}
        return event_types.get(obj.event_type)


class AssessmentChangeFilterSet(BaseAPIFilterSet):
    user = ModelChoiceFilter(queryset=user_choice_qs)
    event_on = DateTimeFromToRangeFilter()

    class Meta:
        model = AssessmentChange
        exclude = []


class AssessmentChangeViewSet(BaseAPIViewSet):
    ordering = ["assessment", "event_on", "event_type"]
    serializer_class = AssessmentChangeSerializer
    filter_class = AssessmentChangeFilterSet
    search_fields = ["assessment_name", "user__username"]
    permission_classes = [
        ReadOnly,
    ]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, AssessmentChange)


class CollaboratorSerializer(BaseAPISerializer):
    user = PrimaryKeyExpandedField(
        queryset=user_choice_qs,
        default=serializers.CurrentUserDefault(),
        serializer=UserSerializer,
    )
    assessment = PrimaryKeyExpandedField(
        queryset=Assessment.objects.all(),
        serializer=ReadOnlyChoiceSerializer,
    )

    class Meta:
        model = Collaborator
        exclude = []


class CollaboratorFilterSet(BaseAPIFilterSet):
    user = ModelChoiceFilter(queryset=user_choice_qs)

    class Meta:
        model = Collaborator
        exclude = []


class CollaboratorViewSet(BaseAPIViewSet):
    ordering = ["assessment", "user"]
    serializer_class = CollaboratorSerializer
    filter_class = CollaboratorFilterSet
    search_fields = ["assessment__name", "user__username"]
    permission_classes = [
        CollaboratorReadOnlyOrAuthenticatedUserPermission,
    ]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, Collaborator)

    def is_last_admin(self):
        obj = self.get_object()
        assessment = obj.assessment
        admins = Collaborator.objects.filter(
            assessment=assessment, role=Collaborator.ADMIN
        )
        return admins.count() < 2 and obj.pk == admins[0].pk

    def perform_update(self, serializer):
        original_obj = self.get_object()
        new_obj = serializer.validated_data
        # In effect, coerce /collborator/<id>/ PUT to be a PATCH
        if (
            new_obj.get("assessment", original_obj.assessment)
            != original_obj.assessment
        ):
            raise serializers.ValidationError(
                {"assessment": "Collaborator assessment may not be changed"}
            )
        if new_obj.get("user", original_obj.user) != original_obj.user:
            raise serializers.ValidationError(
                {"user": "Collaborator user may not be changed"}
            )
        if self.is_last_admin():
            raise serializers.ValidationError(
                f"You are the last admin for {original_obj.assessment}. Create another admin before you relinquish."
            )
        super().perform_update(serializer)

    def perform_destroy(self, serializer):
        obj = self.get_object()
        assessment = obj.assessment
        if self.is_last_admin():
            raise serializers.ValidationError(
                f"You are the last admin for {assessment}. Create another admin before you relinquish."
            )
        super().perform_destroy(serializer)


class SurveyQuestionLikertSerializer(BaseAPISerializer):
    class Meta:
        model = SurveyQuestionLikert
        exclude = []


class SurveyQuestionLikertFilterSet(BaseAPIFilterSet):
    class Meta:
        model = SurveyQuestionLikert
        exclude = []


class SurveyQuestionLikertViewSet(BaseAPIViewSet):
    queryset = SurveyQuestionLikert.objects.all()
    serializer_class = SurveyQuestionLikertSerializer
    filter_class = SurveyQuestionLikertFilterSet
    permission_classes = [
        ReadOnly,
    ]


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
    permission_classes = [CollaboratorReadOnlyOrAuthenticatedUserPermission]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, SurveyAnswerLikert)

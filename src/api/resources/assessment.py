from django.db.models import Q
from django_filters import DateTimeFromToRangeFilter, ModelChoiceFilter
from rest_framework import serializers
from .base import BaseAPISerializer, BaseAPIFilterSet, BaseAPIViewSet, User
from ..models.assessment import Assessment, AssessmentChange, Collaborator
from ..permissions import (
    ReadOnly,
    AssessmentReadOnlyOrAuthenticatedUserPermission,
    CollaboratorReadOnlyOrAuthenticatedUserPermission,
)
from ..utils.assessment import log_assessment_change


def get_assessment_related_queryset(user, model):
    lookup = model.assessment_lookup
    qs = model.objects.all()
    qry = Q(**{f"{lookup}status__lte": Assessment.PUBLISHED}) & Q(
        **{f"{lookup}data_policy__gte": Assessment.PUBLIC}
    )
    if user.is_authenticated:
        qs = model.objects.prefetch_related(f"{lookup}collaborators")
        qry |= Q(**{f"{lookup}collaborators__user": user})
    return qs.filter(qry)


class AssessmentSerializer(BaseAPISerializer):
    class Meta:
        model = Assessment
        exclude = []


class AssessmentFilterSet(BaseAPIFilterSet):
    person_responsible = ModelChoiceFilter(queryset=User.objects.order_by("username"))

    class Meta:
        model = Assessment
        exclude = ["management_plan_file"]


class AssessmentViewSet(BaseAPIViewSet):
    ordering = ["name", "year"]
    serializer_class = AssessmentSerializer
    filter_class = AssessmentFilterSet
    search_fields = ["name", "management_area_version__name"]
    permission_classes = [
        AssessmentReadOnlyOrAuthenticatedUserPermission,
    ]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, Assessment)

    def perform_create(self, serializer):
        assessment = serializer.save()
        user = self.request.user
        Collaborator.objects.create(
            assessment=assessment, user=user, role=Collaborator.ADMIN
        )

    def perform_update(self, serializer):
        user = self.request.user
        original_assessment = self.get_object()
        edited_assessment = serializer.save()
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
    user = ModelChoiceFilter(queryset=User.objects.order_by("username"))
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
    class Meta:
        model = Collaborator
        exclude = []


class CollaboratorFilterSet(BaseAPIFilterSet):
    user = ModelChoiceFilter(queryset=User.objects.order_by("username"))

    class Meta:
        model = Collaborator
        exclude = []


class CollaboratorViewSet(BaseAPIViewSet):
    queryset = Collaborator.objects.all()
    ordering = ["assessment", "user"]
    serializer_class = CollaboratorSerializer
    filter_class = CollaboratorFilterSet
    search_fields = ["assessment__name", "user__username"]
    permission_classes = [
        CollaboratorReadOnlyOrAuthenticatedUserPermission,
    ]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, Collaborator)

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
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        assessment = instance.assessment
        admins = Collaborator.objects.filter(
            assessment=assessment, role=Collaborator.ADMIN
        )
        if admins.count() < 2:
            raise serializers.ValidationError(
                f"You are the last admin for assessment {assessment}. Create another admin before you relinquish."
            )
        super().perform_destroy(instance)

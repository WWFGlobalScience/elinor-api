from django_filters import DateTimeFromToRangeFilter, ModelChoiceFilter
from .base import BaseAPISerializer, BaseAPIFilterSet, BaseAPIViewSet, User
from ..models.assessment import Assessment, AssessmentChange, Collaborator


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
    queryset = Assessment.objects.all()
    ordering = ["name", "year"]
    serializer_class = AssessmentSerializer
    filter_class = AssessmentFilterSet
    search_fields = ["name", "management_area_version__name"]


class AssessmentChangeSerializer(BaseAPISerializer):
    class Meta:
        model = AssessmentChange
        exclude = []


class AssessmentChangeFilterSet(BaseAPIFilterSet):
    user = ModelChoiceFilter(queryset=User.objects.order_by("username"))
    event_on = DateTimeFromToRangeFilter()

    class Meta:
        model = AssessmentChange
        exclude = []


class AssessmentChangeViewSet(BaseAPIViewSet):
    queryset = AssessmentChange.objects.all()
    ordering = ["assessment", "event_on", "event_type"]
    serializer_class = AssessmentChangeSerializer
    filter_class = AssessmentChangeFilterSet
    search_fields = ["assessment_name", "user__username"]


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

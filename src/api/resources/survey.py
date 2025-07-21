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
    filterset_class = SurveyQuestionLikertFilterSet
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

    # def get_validators(self):
    #     print("Getting validators")
    #     validators = super().get_validators()
    #     print(validators)
    #     return validators
    #
    # def is_valid(self, raise_exception=False):
    #     print("Serializer is_valid called")
    #     return super().is_valid(raise_exception=raise_exception)

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
    filterset_class = SurveyAnswerLikertFilterSet
    search_fields = ["assessment__name", "question__key", "question__attribute__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

    def get_queryset(self):
        # print("get_queryset")
        # qs = get_assessment_related_queryset(self.request.user, SurveyAnswerLikert)
        # print("get_assessment_related_queryset")
        # return qs
        return get_assessment_related_queryset(self.request.user, SurveyAnswerLikert)

    # def post(self, request, *args, **kwargs):
    #     print("post")
    #     return self.create(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """
        `.dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
                print(handler)
            else:
                handler = self.http_method_not_allowed

            response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        self.format_kwarg = self.get_format_suffix(**kwargs)

        # Perform content negotiation and store the accepted info on the request
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg

        # Determine the API version, if versioning is in use.
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme

        # Ensure that the incoming request is permitted
        self.perform_authentication(request)
        # self.check_permissions(request)
        print("initial")
        self.check_throttles(request)

    def create(self, request, *args, **kwargs):
        print("create")
        return super().create(request, *args, **kwargs)
        # serializer = self.get_serializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # self.perform_create(serializer)
        # headers = self.get_success_headers(serializer.data)
        # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        # Issue: POSTing to this endpoint calls create() which triggers is_valid()
        # recent DRF upgrade: calls unique together validator on serializer level
        # based on unique_together model Meta property, not the model validate_unique method.
        # And, it does this without calling the serializer validate() function.
        # Solution: create serializer-level unique together validator equivalent to model validate_unique method
        # Should then be able to remove call to full_clean() and custom validate() method.
        # Or: custom is_valid that calls full_clean?
        # Can ensure validation happens from is_valid, and that translated unique_together works for Region
        # But still cannot reproduce Shinta's survey answer problem.

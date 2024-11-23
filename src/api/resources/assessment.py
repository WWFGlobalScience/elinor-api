import io
from datetime import datetime
from django.conf import settings
from django.http import FileResponse
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from django_filters import (
    ChoiceFilter,
    DateTimeFromToRangeFilter,
    ModelChoiceFilter,
    NumberFilter,
)
from pathlib import Path
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from .base import (
    BaseAPISerializer,
    BaseAPIFilterSet,
    BaseAPIViewSet,
    user_choice_qs,
    PrimaryKeyExpandedField,
    ReadOnlyChoiceSerializer,
    UserSerializer,
)
from ..ingest import (
    ingest_400,
    MISSING_FILE,
    UNSUPPORTED_FILE_TYPE,
    FILE_TOO_LARGE,
    UNSUPPORTED_ZIP,
    INVALID_ZIP,
)
from ..ingest.xlsx import AssessmentXLSX
from ..models import (
    Assessment,
    AssessmentChange,
    AssessmentFlag,
    Collaborator,
    ManagementArea,
    Organization,
)
from ..permissions import (
    ReadOnly,
    ReadOnlyOrAuthenticatedCreate,
    AssessmentReadOnlyOrAuthenticatedUserPermission,
    CollaboratorReadOnlyOrAuthenticatedUserPermission,
)
from ..utils import truthy, unzip_file
from ..utils.assessment import (
    assessment_score,
    assessment_xlsx_has_errors,
    attribute_scores,
    enforce_required_attributes,
    get_assessment_related_queryset,
    log_assessment_change,
    notify_assessment_checkout,
)


class AssessmentCollaboratorSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Collaborator
        fields = ["id", "user", "role"]


class AssessmentMASerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = ManagementArea
        fields = [
            "id",
            "name",
            "countries",
            "regions",
            "date_established",
            "recognition_level",
            "governance_type",
            "objectives",
            "management_authority",
            "support_sources",
        ]


class AssessmentFlagListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentFlag
        exclude = []


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
    flags = AssessmentFlagListSerializer(
        many=True, read_only=True, source="assessment_flags"
    )
    collaborators = AssessmentCollaboratorSerializer(many=True, read_only=True)
    management_area_countries = AssessmentMASerializer(
        read_only=True, source="management_area"
    )
    percent_complete = serializers.ReadOnlyField()
    published_version = serializers.StringRelatedField(read_only=True)
    score = serializers.SerializerMethodField()

    # noinspection PyMethodMayBeStatic
    def get_score(self, obj):
        return assessment_score(attribute_scores(obj))

    def validate_checkout(self, value):
        request_user = self.context["request"].user

        if value is not None and value != request_user:
            raise serializers.ValidationError(
                "May not set checkout to a user other than the requester."
            )

        return value

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
    filterset_class = AssessmentFilterSet
    search_fields = ["name", "management_area__name"]
    permission_classes = [AssessmentReadOnlyOrAuthenticatedUserPermission]

    def get_queryset(self):
        return get_assessment_related_queryset(
            self.request.user, Assessment
        ).prefetch_related("assessment_flags")

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
        notify_assessment_checkout(original_assessment, edited_assessment, user)

    @action(detail=True, methods=["GET", "POST"])
    def xlsx(self, request, pk, *args, **kwargs):
        assessment = self.get_object()
        assessment_xlsx = AssessmentXLSX(assessment)

        if request.method == "GET":
            assessment_xlsx.generate_from_assessment()
            response_file = io.BytesIO()
            assessment_xlsx.workbook.save(response_file)
            response_file.seek(0)
            response = FileResponse(
                response_file, content_type=settings.EXCEL_MIME_TYPES[0]
            )
            response["Content-Length"] = len(response_file.getvalue())
            date_string = str(datetime.now().date().isoformat())
            filename = f"elinor-assessment-{assessment.pk}_{date_string}"
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return response

        if request.method == "POST":
            uploaded_file = request.FILES.get("file")
            xlsxfile = uploaded_file
            dryrun = truthy(request.data.get("dryrun"))
            supported_mime_types = settings.EXCEL_MIME_TYPES + settings.ZIP_MIME_TYPES

            if uploaded_file is None:
                error = ingest_400(MISSING_FILE, "missing file")
                return Response(error, status=status.HTTP_400_BAD_REQUEST)
            content_type = uploaded_file.content_type
            if content_type not in supported_mime_types:
                error = ingest_400(
                    UNSUPPORTED_FILE_TYPE,
                    f"file type not supported; supported types: {', '.join(supported_mime_types)}",
                    {"supported_mime_types": supported_mime_types},
                )
                return Response(error, status=status.HTTP_400_BAD_REQUEST)
            maximum_filesize = 10485760  # 10MB
            if uploaded_file.size > maximum_filesize:
                error = ingest_400(
                    FILE_TOO_LARGE,
                    f"uploaded file larger than {maximum_filesize}",
                    {"maximum_filesize": maximum_filesize},
                )
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

            if content_type in settings.ZIP_MIME_TYPES:
                with TemporaryDirectory() as tempdir:
                    temppath = Path(tempdir)
                    try:
                        dirs, files = unzip_file(uploaded_file, temppath)
                        if len(files) != 1:
                            error = ingest_400(
                                UNSUPPORTED_ZIP,
                                "zip file contains more than one file, or is empty",
                                {"num_files": len(files)},
                            )
                            return Response(error, status=status.HTTP_400_BAD_REQUEST)
                    except BadZipFile as e:
                        error = ingest_400(INVALID_ZIP, str(e))
                        return Response(error, status=status.HTTP_400_BAD_REQUEST)

                    with open(files[0], "rb") as f:
                        xlsxfile = io.BytesIO(f.read())

            assessment_xlsx.load_from_file(xlsxfile)
            if assessment_xlsx_has_errors(assessment_xlsx):
                return Response(
                    assessment_xlsx.validations, status=status.HTTP_400_BAD_REQUEST
                )
            assessment_xlsx.submit_answers(dryrun=dryrun)
            if assessment_xlsx_has_errors(assessment_xlsx):
                return Response(
                    assessment_xlsx.validations, status=status.HTTP_400_BAD_REQUEST
                )

            return Response("Success", status=status.HTTP_200_OK)


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
    filterset_class = AssessmentChangeFilterSet
    search_fields = ["assessment_name", "user__username"]
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return get_assessment_related_queryset(self.request.user, AssessmentChange)


class AssessmentFlagSerializer(BaseAPISerializer):
    class Meta:
        model = AssessmentFlag
        exclude = []


class AssessmentFlagFilterSet(BaseAPIFilterSet):
    class Meta:
        model = AssessmentFlag
        exclude = []


class AssessmentFlagViewSet(BaseAPIViewSet):
    serializer_class = AssessmentFlagSerializer
    filterset_class = AssessmentFlagFilterSet
    search_fields = ["assessment_name", "reporter__username"]
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def get_queryset(self):
        return AssessmentFlag.objects.all()


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
    filterset_class = CollaboratorFilterSet
    search_fields = ["assessment__name", "user__username"]
    permission_classes = [CollaboratorReadOnlyOrAuthenticatedUserPermission]

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

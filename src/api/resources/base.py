from collections import OrderedDict
from allauth.account.admin import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.contrib.auth import get_user_model
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from django_filters import (
    CharFilter,
    ChoiceFilter,
    DateTimeFromToRangeFilter,
    FilterSet,
    ModelChoiceFilter,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_rest_auth.registration.serializers import RegisterSerializer
from ..models import (
    GovernanceType,
    ManagementAuthority,
    Organization,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)
from ..permissions import AuthenticatedAndReadOnly, ReadOnlyOrAuthenticatedCreate


User = get_user_model()
user_choice_qs = User.objects.order_by("username")


class APIRootView(routers.APIRootView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ElinorDefaultRouter(routers.DefaultRouter):
    APIRootView = APIRootView

    def get_api_root_view(self, api_urls=None):
        api_root_dict = OrderedDict()
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        return self.APIRootView.as_view(api_root_dict=api_root_dict)


class StandardResultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 1000


class BaseAPISerializer(serializers.ModelSerializer):
    created_on = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_on = serializers.DateTimeField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
            validated_data["updated_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["updated_by"] = request.user
        return super().update(instance, validated_data)


class BaseAPIFilterSet(FilterSet):
    created_on = DateTimeFromToRangeFilter()
    created_by = ModelChoiceFilter(queryset=user_choice_qs)
    updated_on = DateTimeFromToRangeFilter()
    updated_by = ModelChoiceFilter(queryset=user_choice_qs)


class ChoiceFilterSet(BaseAPIFilterSet):
    name = CharFilter()


class BaseAPIViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)


class BaseChoiceViewSet(BaseAPIViewSet):
    ordering = ["name"]
    filter_class = ChoiceFilterSet
    search_fields = ["name"]
    permission_classes = [
        ReadOnlyOrAuthenticatedCreate,
    ]


class ReadOnlyChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)


class UserSerializer(BaseAPISerializer):
    last_login = serializers.ReadOnlyField()
    affiliation = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Organization.objects.all(),
        required=False,
        source="profile.affiliation",
    )
    accept_tor = serializers.BooleanField(
        label="Accept ToR", required=False, source="profile.accept_tor"
    )
    created_on = serializers.DateTimeField(read_only=True, source="profile.created_on")
    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
        source="profile.created_by",
    )
    updated_on = serializers.DateTimeField(read_only=True, source="profile.updated_on")
    updated_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
        source="profile.updated_by",
    )

    def _create_or_update_profile(self, user, profile_data, create=False):
        current_user = user
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            current_user = request.user
        if hasattr(user, "profile") and profile_data:
            profile = user.profile
            profile.affiliation = profile_data.get("affiliation", profile.affiliation)
            profile.accept_tor = profile_data.pop("accept_tor", profile.accept_tor)
            if create:
                profile.created_by = current_user
            profile.updated_by = current_user
            profile.save()

        return user

    def create(self, validated_data):
        profile_data = validated_data.pop("profile", None)
        user = super().create(validated_data)
        return self._create_or_update_profile(user, profile_data, True)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        user = super().update(instance, validated_data)
        return self._create_or_update_profile(user, profile_data)

    class Meta:
        model = User
        exclude = [
            "groups",
            "user_permissions",
            "password",
            "is_staff",
            "is_active",
            "email",
        ]
        read_only_fields = ["date_joined", "is_superuser"]


# for dj-rest-auth
class UserRegistrationSerializer(RegisterSerializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    affiliation = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Organization.objects.all(),
    )
    accept_tor = serializers.BooleanField(
        label="Accept ToR",
    )

    def save(self, request):
        first_name = self.validated_data.get("first_name")
        last_name = self.validated_data.get("last_name")
        affiliation = self.validated_data.get("affiliation")
        accept_tor = self.validated_data.get("accept_tor", False)
        if not accept_tor:
            missing_tor_message = "The Terms of Reference must be accepted in order to register a new account"
            # This does the right thing but does cause a 500 when wrapped in the DRF html view
            raise serializers.ValidationError(missing_tor_message)
        user = super().save(request)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        profile = user.profile
        profile.affiliation = affiliation
        profile.accept_tor = accept_tor
        profile.created_by = user
        profile.updated_by = user
        profile.save()

        return user


class NewEmailConfirmation(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_object_or_404(User, email=request.data["email"])
        emailAddress = EmailAddress.objects.filter(user=user, verified=True).exists()

        if emailAddress:
            return Response(
                {"message": "This email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            try:
                send_email_confirmation(request, user=user)
                return Response(
                    {"message": "Email confirmation sent"},
                    status=status.HTTP_201_CREATED,
                )
            except APIException:
                return Response(
                    {
                        "message": "This email does not exist, please create a new account"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )


class UserFilterSet(FilterSet):
    # created_on = DateTimeFromToRangeFilter(
    #     field_name="profile__created_on", label="created_on"
    # )
    # created_by = ModelChoiceFilter(
    #     queryset=user_choice_qs,
    #     field_name="profile__created_by",
    #     label="created_by",
    # )
    # updated_on = DateTimeFromToRangeFilter(
    #     field_name="profile__updated_on", label="updated_on"
    # )
    # updated_by = ModelChoiceFilter(
    #     queryset=user_choice_qs,
    #     field_name="profile__updated_by",
    #     label="updated_by",
    # )
    # last_login = DateTimeFromToRangeFilter()
    # date_joined = DateTimeFromToRangeFilter()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]
        # exclude = ["groups", "user_permissions", "password"]


class UserViewSet(BaseAPIViewSet):
    http_method_names = [option.lower() for option in permissions.SAFE_METHODS]
    permission_classes = [
        AuthenticatedAndReadOnly,
    ]
    queryset = User.objects.all()
    ordering = ["username"]
    serializer_class = UserSerializer
    filter_class = UserFilterSet
    search_fields = ["username", "first_name", "last_name"]


class OrganizationSerializer(BaseAPISerializer):
    class Meta:
        model = Organization
        exclude = []


class OrganizationViewSet(BaseChoiceViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class GovernanceTypeSerializer(BaseAPISerializer):
    class Meta:
        model = GovernanceType
        exclude = []


class GovernanceTypeViewSet(BaseChoiceViewSet):
    queryset = GovernanceType.objects.all()
    serializer_class = GovernanceTypeSerializer


class ManagementAuthoritySerializer(BaseAPISerializer):
    class Meta:
        model = ManagementAuthority
        exclude = []


class ManagementAuthorityViewSet(BaseChoiceViewSet):
    queryset = ManagementAuthority.objects.all()
    serializer_class = ManagementAuthoritySerializer


class ProtectedAreaSerializer(BaseAPISerializer):
    class Meta:
        model = ProtectedArea
        exclude = []


class ProtectedAreaFilterSet(ChoiceFilterSet):
    class Meta:
        model = ProtectedArea
        exclude = []


class ProtectedAreaViewSet(BaseChoiceViewSet):
    queryset = ProtectedArea.objects.all()
    serializer_class = ProtectedAreaSerializer
    filter_class = ProtectedAreaFilterSet


class RegionSerializer(CountryFieldMixin, BaseAPISerializer):
    class Meta:
        model = Region
        exclude = []


class RegionFilterSet(ChoiceFilterSet):
    country = ChoiceFilter(choices=countries)

    class Meta:
        model = Region
        exclude = []


class RegionViewSet(BaseChoiceViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    filter_class = RegionFilterSet


class StakeholderGroupSerializer(BaseAPISerializer):
    class Meta:
        model = StakeholderGroup
        exclude = []


class StakeholderGroupViewSet(BaseChoiceViewSet):
    queryset = StakeholderGroup.objects.all()
    serializer_class = StakeholderGroupSerializer


class SupportSourceSerializer(BaseAPISerializer):
    class Meta:
        model = SupportSource
        exclude = []


class SupportSourceViewSet(BaseChoiceViewSet):
    queryset = SupportSource.objects.all()
    serializer_class = SupportSourceSerializer

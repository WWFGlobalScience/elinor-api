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
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from ..models import (
    GovernanceType,
    ManagementAuthority,
    Organization,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)


User = get_user_model()


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
    created_by = ModelChoiceFilter(queryset=User.objects.order_by("username"))
    updated_on = DateTimeFromToRangeFilter()
    updated_by = ModelChoiceFilter(queryset=User.objects.order_by("username"))


class ChoiceFilterSet(BaseAPIFilterSet):
    name = CharFilter()


class BaseAPIViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)


class BaseChoiceViewSet(BaseAPIViewSet):
    ordering = ["name"]
    filter_class = ChoiceFilterSet
    search_fields = ["name"]


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
        exclude = ["groups", "user_permissions"]


class UserFilterSet(FilterSet):
    created_on = DateTimeFromToRangeFilter(
        field_name="profile__created_on", label="created_on"
    )
    created_by = ModelChoiceFilter(
        queryset=User.objects.order_by("username"),
        field_name="profile__created_by",
        label="created_by",
    )
    updated_on = DateTimeFromToRangeFilter(
        field_name="profile__updated_on", label="updated_on"
    )
    updated_by = ModelChoiceFilter(
        queryset=User.objects.order_by("username"),
        field_name="profile__updated_by",
        label="updated_by",
    )
    last_login = DateTimeFromToRangeFilter()
    date_joined = DateTimeFromToRangeFilter()

    class Meta:
        model = User
        exclude = ["groups", "user_permissions", "password"]


class UserViewSet(BaseAPIViewSet):
    queryset = User.objects.all()
    ordering = ["username"]
    serializer_class = UserSerializer
    filter_class = UserFilterSet
    search_fields = ["username", "first_name", "last_name", "email"]


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

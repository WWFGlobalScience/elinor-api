from collections import OrderedDict
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from django_filters import (
    CharFilter,
    ChoiceFilter,
    DateFromToRangeFilter,
    DateTimeFromToRangeFilter,
    FilterSet,
    ModelChoiceFilter,
)
from django_filters.rest_framework import DjangoFilterBackend
from modeltranslation.fields import TranslationField
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import (
    ActiveLanguage,
    AssessmentVersion,
    Attribute,
    Document,
    GovernanceType,
    ManagementAuthority,
    Organization,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
)
from ..permissions import (
    AuthenticatedAndReadOnly,
    ReadOnly,
    ReadOnlyOrAuthenticatedCreate,
)

try:
    from allauth.account.utils import send_email_confirmation, setup_user_email
    from allauth.account.models import EmailAddress
except ImportError:
    raise ImportError("allauth needs to be added to INSTALLED_APPS.")


User = get_user_model()
user_choice_qs = User.objects.order_by("username")


@api_view(["GET", "HEAD", "OPTIONS"])
@authentication_classes([])
@permission_classes((AllowAny,))
def health(request):
    return Response("ok")


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


class PrimaryKeyExpandedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        self.serializer = kwargs.pop("serializer", None)
        if self.serializer is not None and not issubclass(
            self.serializer, serializers.Serializer
        ):
            raise TypeError('"serializer" is not a valid serializer class')

        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return False if self.serializer else True

    def to_representation(self, instance):
        if self.serializer:
            return self.serializer(instance, context=self.context).data
        return super().to_representation(instance)

    # Same as RelatedField.get_choices except that `item.pk` is the key
    # instead of `self.to_representation(item)`
    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([(item.pk, self.display_value(item)) for item in queryset])


class BaseAPISerializer(serializers.ModelSerializer):
    created_on = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_on = serializers.DateTimeField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            modelfields = self.Meta.model._meta.fields
            for field in modelfields:
                if isinstance(field, TranslationField):
                    self.fields.pop(field.name)

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


class DefaultOrderingFilter(OrderingFilter):
    # ensure unique pagination when not enough ordering fields are specified; requires "id" field
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view) or []
        if "id" not in ordering:
            ordering.append("id")
        return ordering


class BaseAPIViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    filter_backends = (DjangoFilterBackend, DefaultOrderingFilter, SearchFilter)


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

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class UserSerializer(BaseAPISerializer):
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


class SelfSerializer(UserSerializer):
    last_login = serializers.ReadOnlyField()

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
        raise MethodNotAllowed("POST")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        # email: validation already applied; saved to both user and EmailAddress
        incoming_email = validated_data.get("email")
        resetup_email = False
        if incoming_email and incoming_email != instance.email:
            resetup_email = True

        user = super().update(instance, validated_data)
        user = self._create_or_update_profile(user, profile_data)

        if resetup_email:
            request = self.context.get("request")
            EmailAddress.objects.filter(user=user).delete()
            setup_user_email(request, user, [])
            send_email_confirmation(request, user, False, incoming_email)
            try:
                request.user.auth_token.delete()
            except (AttributeError, ObjectDoesNotExist):
                pass

        return user

    class Meta:
        model = User
        exclude = [
            "groups",
            "user_permissions",
            "password",
            "is_staff",
            "is_active",
        ]
        read_only_fields = ["date_joined", "is_superuser"]


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
    http_method_names = [method.lower() for method in permissions.SAFE_METHODS]
    permission_classes = [
        AuthenticatedAndReadOnly,
    ]
    ordering = ["username"]
    serializer_class = UserSerializer
    filter_class = UserFilterSet
    search_fields = ["username", "first_name", "last_name"]

    def get_queryset(self):
        return User.objects.all()


@api_view(permissions.SAFE_METHODS)
@authentication_classes([])
@permission_classes((ReadOnly,))
def assessmentversion(request):
    current_version = AssessmentVersion.objects.order_by(
        "-year", "-major_version"
    ).first()
    return Response(str(current_version))


class ActiveLanguageSerializer(BaseAPISerializer):
    class Meta:
        model = ActiveLanguage
        exclude = []


class ActiveLanguageViewset(BaseAPIViewSet):
    serializer_class = ActiveLanguageSerializer
    permission_classes = [ReadOnly]
    ordering = ["code", "name"]

    def get_queryset(self):
        return ActiveLanguage.objects.filter(active=True)


class AttributeSerializer(BaseAPISerializer):
    class Meta:
        model = Attribute
        exclude = []


class AttributeFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Attribute
        exclude = []


class AttributeViewSet(BaseChoiceViewSet):
    serializer_class = AttributeSerializer
    filter_class = AttributeFilterSet
    permission_classes = [ReadOnly]
    ordering = ["order", "name"]

    def get_queryset(self):
        return Attribute.objects.all()


class DocumentSerializer(BaseAPISerializer):
    version = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Document
        exclude = []


class DocumentFilterSet(BaseAPIFilterSet):
    publication_date = DateFromToRangeFilter()

    class Meta:
        model = Document
        exclude = ["file"]


class DocumentViewSet(BaseAPIViewSet):
    serializer_class = DocumentSerializer
    filter_class = DocumentFilterSet
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return Document.objects.all()


class GovernanceTypeSerializer(BaseAPISerializer):
    class Meta:
        model = GovernanceType
        exclude = []


class GovernanceTypeViewSet(BaseChoiceViewSet):
    serializer_class = GovernanceTypeSerializer

    def get_queryset(self):
        return GovernanceType.objects.all()


class ManagementAuthoritySerializer(BaseAPISerializer):
    class Meta:
        model = ManagementAuthority
        exclude = []


class ManagementAuthorityViewSet(BaseChoiceViewSet):
    serializer_class = ManagementAuthoritySerializer

    def get_queryset(self):
        return ManagementAuthority.objects.all()


class OrganizationSerializer(BaseAPISerializer):
    class Meta:
        model = Organization
        exclude = []


class OrganizationViewSet(BaseChoiceViewSet):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.all()


class ProtectedAreaSerializer(BaseAPISerializer):
    class Meta:
        model = ProtectedArea
        exclude = []


class ProtectedAreaViewSet(BaseChoiceViewSet):
    serializer_class = ProtectedAreaSerializer
    filter_class = ChoiceFilterSet

    def get_queryset(self):
        return ProtectedArea.objects.all()


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
    serializer_class = RegionSerializer
    filter_class = RegionFilterSet

    def get_queryset(self):
        return Region.objects.all()


class StakeholderGroupSerializer(BaseAPISerializer):
    class Meta:
        model = StakeholderGroup
        exclude = []


class StakeholderGroupViewSet(BaseChoiceViewSet):
    serializer_class = StakeholderGroupSerializer

    def get_queryset(self):
        return StakeholderGroup.objects.all()


class SupportSourceSerializer(BaseAPISerializer):
    class Meta:
        model = SupportSource
        exclude = []


class SupportSourceViewSet(BaseChoiceViewSet):
    serializer_class = SupportSourceSerializer

    def get_queryset(self):
        return SupportSource.objects.all()

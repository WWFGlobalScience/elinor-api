from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from .models.assessment import Assessment, Collaborator
from .utils import get_m2m_fields


def get_assessment_or_none(obj):
    assessment = None
    if hasattr(obj, "assessment_lookup"):
        assessment = obj
        if obj.assessment_lookup != "":
            try:
                assessment = getattr(obj, obj.assessment_lookup)
            except ObjectDoesNotExist:
                return None
    return assessment


def get_collaborator(assessment, user):
    try:
        return Collaborator.objects.get(assessment=assessment, user=user)
    except Collaborator.DoesNotExist:
        raise PermissionDenied(f"User {user} is not part of assessment {assessment}.")


class DefaultPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return False


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return request.method in permissions.SAFE_METHODS or user.is_superuser


class AuthenticatedAndReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (
            request.method in permissions.SAFE_METHODS or user.is_superuser
        )


class ReadOnlyOrAuthenticatedCreate(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated and (request.method == "POST" or user.is_superuser)


class AssessmentReadOnlyOrAuthenticatedUserPermission(permissions.BasePermission):
    PUBLISHED_MODIFIABLE_FIELDS = [
        "data_policy",
        "strengths_explanation",
        "needs_explanation",
        "context",
    ]

    def user_assessment_permissions(self, request, serializer, obj, user):
        assessment = get_assessment_or_none(obj)
        if assessment:
            # If existing assessment is already checked out by another user, 403
            if assessment.checkout is not None and assessment.checkout != user:
                raise PermissionDenied(
                    f"Assessment {assessment} is checked out by {assessment.checkout}."
                )

            user_collaborator = get_collaborator(assessment, user)
            if user_collaborator.is_admin:
                if not assessment.is_finalized:
                    return True
                elif serializer:
                    return (
                        set(serializer.validated_data.keys()).issubset(
                            self.PUBLISHED_MODIFIABLE_FIELDS
                        )
                        and request.method != "DELETE"
                    )
            elif user_collaborator.is_collector:
                return not assessment.is_finalized and request.method != "DELETE"

        return user.is_authenticated

    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS or user.is_superuser:
            return True

        if request.method == "POST" and view.basename != "assessment":
            model_class = view.get_queryset().model
            m2m_fields = get_m2m_fields(model_class)
            # Strip out m2m fields that are likely used in PrimaryKeyExpandedField
            # GET representations inappropriate for model instantiation
            non_m2m_data = {
                k: v for k, v in request.data.items() if k not in m2m_fields
            }
            serializer = view.get_serializer(data=non_m2m_data)
            serializer.is_valid(raise_exception=True)
            obj = model_class(**serializer.validated_data)
            # check perms for the assessment related to proposed new obj
            return self.user_assessment_permissions(request, serializer, obj, user)

        return user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS or user.is_superuser:
            return True

        serializer = None
        if request.method in ("PUT", "PATCH"):
            partial = request.method == "PATCH"
            serializer = view.get_serializer(obj, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
        return self.user_assessment_permissions(request, serializer, obj, user)


class CollaboratorReadOnlyOrAuthenticatedUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS or user.is_superuser:
            return True

        if request.method == "POST":
            assessment_id = request.data.get("assessment")
            try:
                assessment = Assessment.objects.get(pk=assessment_id)
            except Assessment.DoesNotExist:
                raise serializers.ValidationError(
                    {"assessment": "Missing assessment id"}
                )
            user_collaborator = get_collaborator(assessment, user)
            return user_collaborator.is_admin
        return user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS or user.is_superuser:
            return True

        user_collaborator = get_collaborator(obj.assessment, user)
        return user_collaborator.is_admin

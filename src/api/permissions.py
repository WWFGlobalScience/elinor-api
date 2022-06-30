from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from .models.assessment import Assessment, Collaborator


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
    PUBLISHED_MODIFIABLE_FIELDS = ["data_policy"]

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS or user.is_superuser:
            return True

        assessment = get_assessment_or_none(obj)
        if assessment:
            collaborator = get_collaborator(assessment, user)
            if collaborator.is_admin:
                if not assessment.is_published:
                    return True
                elif request.method in ("PUT", "PATCH"):
                    partial = request.method == "PATCH"
                    serializer = view.get_serializer(
                        obj, data=request.data, partial=partial
                    )
                    serializer.is_valid(raise_exception=True)
                    return set(serializer.validated_data.keys()).issubset(
                        self.PUBLISHED_MODIFIABLE_FIELDS
                    )
            elif collaborator.is_collector:
                return not assessment.is_published and request.method in (
                    "PUT",
                    "PATCH",
                )

        return False


class CollaboratorReadOnlyOrAuthenticatedUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if user.is_authenticated:
            if request.method == "POST":
                assessment_id = request.data.get("assessment")
                try:
                    assessment = Assessment.objects.get(pk=assessment_id)
                except Assessment.DoesNotExist:
                    raise serializers.ValidationError(
                        {"assessment": "Missing assessment id"}
                    )
                user_collaborator = get_collaborator(assessment, user)
                return not assessment.is_published and user_collaborator.is_admin
            return True  # PUT/PATCH/DELETE handled with object permissions

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated:
            if user.is_superuser:
                return True
            user_collaborator = get_collaborator(obj.assessment, user)
            return not obj.assessment.is_published and user_collaborator.is_admin

        return False

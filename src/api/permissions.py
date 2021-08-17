from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from .models.assessment import Assessment, Collaborator


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


class ReadOnlyOrAuthenticatedCreateOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated

    # has_permission checks (handling SAFE_METHODS + POST) have already passed
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated:
            return user == obj.created_by or user.is_superuser
        return False


class AssessmentReadOnlyOrAuthenticatedUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated:
            if user.is_superuser:
                return True
            collaborator = get_collaborator(obj, user)
            if collaborator.is_admin:
                return not obj.is_published
            elif collaborator.is_collector:
                return not obj.is_published and request.method in ("PUT", "PATCH")

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

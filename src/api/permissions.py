from rest_framework import permissions


class IsAuthenticatedAndReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and request.method in permissions.SAFE_METHODS

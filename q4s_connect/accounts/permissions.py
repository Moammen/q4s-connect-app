from rest_framework.permissions import BasePermission

# Custom permissions for user roles

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser
class IsEngineer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "engineer"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"

class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "operator"


class IsActiveUser(BasePermission):
    """
    Global gate that rejects soft-deleted users on every protected endpoint.
    Pairs with IsAuthenticated in DEFAULT_PERMISSION_CLASSES so any user whose
    is_deleted=True cannot use any API regardless of a still-valid JWT.
    """
    message = "User account has been deleted."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return not getattr(user, "is_deleted", False)

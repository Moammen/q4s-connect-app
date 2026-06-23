import django_filters
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    UserSerializer,
    UserWithLoggerCountSerializer,
    ETSTokenObtainPairSerializer,
)
from .permissions import IsSuperAdmin, IsEngineer, IsAdmin

# Views for user management and profile retrieval


# Filter class for user listing with search by name, role, and is_deleted.
# `is_deleted` lets clients explicitly request deleted users via
# ?is_deleted=true (or only active via ?is_deleted=false). When the param
# is absent, filter_queryset() hides soft-deleted users by default.
class UserFilter(django_filters.FilterSet):
    name       = django_filters.CharFilter(method="filter_by_name")
    is_deleted = django_filters.BooleanFilter(field_name="is_deleted")

    class Meta:
        model = User
        fields = ["role"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # Default: hide soft-deleted users unless ?is_deleted=... is passed
        if "is_deleted" not in self.data:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def filter_by_name(self, queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value)
        )


# ViewSet for managing users with full CRUD operations.
# DELETE on this viewset performs a HARD delete (row is removed).
# Soft delete and restore are handled by dedicated APIView endpoints below.
class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin | IsAdmin | IsEngineer]
    filterset_class = UserFilter


# Read-only ViewSet to list users with their data logger counts
class UserWithDataLoggerCountViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserWithLoggerCountSerializer
    permission_classes = [IsSuperAdmin | IsAdmin | IsEngineer]
    filterset_class = UserFilter


# Soft delete endpoint — sets is_deleted=True without removing the row.
class UserSoftDeleteView(APIView):
    """
    POST /api/users/<id>/soft-delete/
    Restricted to super admins. Idempotency-aware: already-deleted users
    return 400 instead of silently re-deleting.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user.is_deleted:
            return Response(
                {"detail": "User is already soft-deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_deleted = True
        user.save(update_fields=["is_deleted"])
        return Response(
            {"detail": "User soft-deleted.", "user_id": user.id},
            status=status.HTTP_200_OK,
        )


# Restore endpoint — reverses a soft delete.
class UserRestoreView(APIView):
    """
    POST /api/users/<id>/restore/
    Restricted to super admins. Queries User directly (no get_queryset filter)
    so soft-deleted rows can be found and undeleted.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not user.is_deleted:
            return Response(
                {"detail": "User is not deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_deleted = False
        user.save(update_fields=["is_deleted"])
        return Response(
            {"detail": "User restored.", "user_id": user.id},
            status=status.HTTP_200_OK,
        )


# Custom JWT login view that rejects soft-deleted users
class ETSTokenObtainPairView(TokenObtainPairView):
    serializer_class = ETSTokenObtainPairSerializer


# API endpoint to retrieve the authenticated user's profile information
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

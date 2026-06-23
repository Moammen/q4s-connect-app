from django.contrib.auth.hashers import check_password
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator

from rest_framework import status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_ratelimit.decorators import ratelimit

from .models import (
    OPCGeneratedSiteLink,
)
from .serializers import (
    OPCGeneratedSiteLinkSerializer,
)


class OPCGeneratedSiteLinkViewSet(viewsets.ModelViewSet):
    queryset = OPCGeneratedSiteLink.objects.all()
    serializer_class = OPCGeneratedSiteLinkSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]


@method_decorator(
    ratelimit(),
    name="post",
)
class SiteDashboardAccessView(APIView):
    """
    POST /api/site-dashboard/<link_id>/access/
    Header: Authorization: Bearer <password>

    Order of checks:
      1. link exists + not deleted + is_active   -> 404 NOT_FOUND
      2. not expired                             -> 410 EXPIRED
      3. Bearer password matches password_hash   -> 401 INVALID_CREDENTIALS
      4. ok                                       -> 200 + full snapshot
    """
    authentication_classes = []
    permission_classes     = []

    def post(self, request, link_id):
        link = OPCGeneratedSiteLink.objects.filter(
            pk=link_id, is_deleted=False, is_active=True,
        ).first()
        if link is None:
            return Response(
                {"ok": False, "error": {"code": "NOT_FOUND",
                                        "message": "Link not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if link.expire_date <= timezone.now():
            return Response(
                {"ok": False, "error": {"code": "EXPIRED",
                                        "message": "Link expired."}},
                status=status.HTTP_410_GONE,
            )

        auth = request.META.get("HTTP_AUTHORIZATION", "")
        
        password = auth[7:].strip() if auth.startswith("Bearer ") else ""

        if not password or not check_password(password, link.password_hash):
            return Response(
                {"ok": False, "error": {"code": "INVALID_CREDENTIALS",
                                        "message": "Invalid password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "ok":          True,
                "id":          link.id,
                "site":        link.site,
                "username":    link.username,
                "expire_date": link.expire_date,
                "filter":      {
                    "from": link.filter_start_date,
                    "to":   link.filter_end_date,
                },
                "data":        link.json_data,
            },
            status=status.HTTP_200_OK,
        )
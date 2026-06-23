import django_filters
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ETSSite, ETSSiteBillingConfig, ETSSiteBilling
from .serializers import ETSSiteSerializer, ETSSiteBillingConfigSerializer, ETSSiteBillingSerializer
import datetime
from opc.models import OPCAlarmLive, OPCAlarmEvent, OPCAsset
from opc.serializers import OPCAlarmLiveSerializer
from core.models import ETSSite
from opc.helpers import get_energy_mwh4_daily_accumulated, get_low_delta_t_sites_cached
from accounts.permissions import IsSuperAdmin


class ETSSiteFilter(django_filters.FilterSet):
    name          = django_filters.CharFilter(field_name="name",          lookup_expr="icontains")
    location      = django_filters.CharFilter(field_name="location",      lookup_expr="icontains")
    customer_name = django_filters.CharFilter(field_name="customer_name", lookup_expr="icontains")
    ets_code      = django_filters.CharFilter(field_name="ets_code",      lookup_expr="icontains")
    is_deleted    = django_filters.BooleanFilter(field_name="is_deleted")

    class Meta:
        model  = ETSSite
        fields = ["name", "region", "country", "connected", "active", "alarm_status",
                  "ets_code", "location", "customer_name"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # Default: hide soft-deleted sites unless ?is_deleted=... is passed
        if "is_deleted" not in self.data:
            queryset = queryset.filter(is_deleted=False)
        return queryset


class ETSSiteBillingFilter(django_filters.FilterSet):
    is_deleted = django_filters.BooleanFilter(field_name="is_deleted")

    class Meta:
        model  = ETSSiteBilling
        fields = ["ets_site"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # Default: hide soft-deleted billings unless ?is_deleted=... is passed
        if "is_deleted" not in self.data:
            queryset = queryset.filter(is_deleted=False)
        return queryset



class ETSSiteViewSet(ModelViewSet):
    queryset           = ETSSite.objects.all()
    serializer_class   = ETSSiteSerializer
    permission_classes = [IsAuthenticated]
    filterset_class    = ETSSiteFilter

    def get_queryset(self):
        qs   = super().get_queryset()
        user = self.request.user

        if user.is_superuser or user.all_sites:
            return qs

        return qs.filter(pk__in=user.ets_sites.values_list("pk", flat=True))

class ETSSiteBillingConfigViewSet(ModelViewSet):
    queryset           = ETSSiteBillingConfig.objects.all()
    serializer_class   = ETSSiteBillingConfigSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields   = ["ets_site"]


class ETSSiteBillingViewSet(ModelViewSet):
    queryset           = ETSSiteBilling.objects.all()
    serializer_class   = ETSSiteBillingSerializer
    permission_classes = [IsAuthenticated]
    filterset_class    = ETSSiteBillingFilter

# Soft delete / restore for ETSSite ------------------------------------------------
class ETSSiteSoftDeleteView(APIView):
    """
    POST /api/ets-sites/<id>/soft-delete/
    Restricted to super admins.

    Mirrors hard-delete behavior for OPCAsset: any asset linked to this site
    has its ets_site FK set to NULL. The site row remains (with is_deleted=True),
    but the relationship is severed — restoring the site will NOT re-link assets.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            site = ETSSite.objects.get(pk=pk)
        except ETSSite.DoesNotExist:
            return Response({"detail": "ETSSite not found."}, status=status.HTTP_404_NOT_FOUND)
        if site.is_deleted:
            return Response({"detail": "ETSSite is already soft-deleted."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            unlinked = OPCAsset.objects.filter(ets_site=site).update(ets_site=None)
            site.is_deleted = True
            site.save(update_fields=["is_deleted"])

        return Response({
            "detail":           "ETSSite soft-deleted.",
            "site_id":          site.id,
            "unlinked_assets":  unlinked,
        })

class ETSSiteRestoreView(APIView):
    """
    POST /api/ets-sites/<id>/restore/
    Restricted to super admins.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            site = ETSSite.objects.get(pk=pk)
        except ETSSite.DoesNotExist:
            return Response({"detail": "ETSSite not found."}, status=status.HTTP_404_NOT_FOUND)
        if not site.is_deleted:
            return Response({"detail": "ETSSite is not deleted."}, status=status.HTTP_400_BAD_REQUEST)
        site.is_deleted = False
        site.save(update_fields=["is_deleted"])
        return Response({"detail": "ETSSite restored.", "site_id": site.id})

# Soft delete / restore for ETSSiteBilling ----------------------------------------
class ETSSiteBillingSoftDeleteView(APIView):
    """
    POST /api/ets-billing/<id>/soft-delete/
    Restricted to super admins.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            billing = ETSSiteBilling.objects.get(pk=pk)
        except ETSSiteBilling.DoesNotExist:
            return Response({"detail": "ETSSiteBilling not found."}, status=status.HTTP_404_NOT_FOUND)
        if billing.is_deleted:
            return Response({"detail": "ETSSiteBilling is already soft-deleted."}, status=status.HTTP_400_BAD_REQUEST)
        billing.is_deleted = True
        billing.save(update_fields=["is_deleted"])
        return Response({"detail": "ETSSiteBilling soft-deleted.", "billing_id": billing.id})

class ETSSiteBillingRestoreView(APIView):
    """
    POST /api/ets-billing/<id>/restore/
    Restricted to super admins.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        try:
            billing = ETSSiteBilling.objects.get(pk=pk)
        except ETSSiteBilling.DoesNotExist:
            return Response({"detail": "ETSSiteBilling not found."}, status=status.HTTP_404_NOT_FOUND)
        if not billing.is_deleted:
            return Response({"detail": "ETSSiteBilling is not deleted."}, status=status.HTTP_400_BAD_REQUEST)
        billing.is_deleted = False
        billing.save(update_fields=["is_deleted"])
        return Response({"detail": "ETSSiteBilling restored.", "billing_id": billing.id})

class ETSConnectivityView(APIView):
    """
    GET /api/ETS-connectivity/
    Returns connectivity summary for all ETS sites.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Exclude soft-deleted sites from all connectivity counts
        sites = ETSSite.objects.filter(is_deleted=False)
        return Response({
            "total_sites":     sites.count(),
            "active_sites":    sites.filter(active=True).count(),
            "connected_sites": sites.filter(connected=True).count(),
            "alarm_sites":     sites.filter(alarm_status="active").count(),
        })

class DashboardSummaryView(APIView):
    """
    GET /api/dashboard-summary/

    Aggregates:
    - ETS connectivity stats
    - Latest active OPC alarms
    - OPC alarm daily counts
    - Energy MWH4 daily accumulated (last 7 days)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # -------------------------------------------------
        # 1) ETS Connectivity Summary (exclude soft-deleted sites)
        # -------------------------------------------------
        sites = ETSSite.objects.filter(is_deleted=False)

        ets_connectivity = {
            "total_sites":     sites.count(),
            "active_sites":    sites.filter(active=True).count(),
            "connected_sites": sites.filter(connected=True).count(),
            "alarm_sites":     sites.filter(alarm_status="active").count(),
        }

        # -------------------------------------------------
        # 2) Active OPC Alarms (latest 10, exclude soft-deleted rules)
        # -------------------------------------------------
        active_alarms_qs = (
            OPCAlarmLive.objects
            .filter(is_active=True, rule__is_deleted=False,acknowledged=False)
            .select_related("rule", "rule__node")
            .order_by("-activated_at")[:100]
        )
        active_alarms = OPCAlarmLiveSerializer(active_alarms_qs, many=True).data

        # -------------------------------------------------
        # 3) Alarm Daily Count (last 5 days)
        # -------------------------------------------------
        days_count = 5
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days_count - 1)

        since = timezone.make_aware(
            datetime.datetime.combine(start_date, datetime.time.min)
        )

        data = (
            OPCAlarmEvent.objects
            .filter(started_at__gte=since, rule__is_deleted=False)
            .annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        counts_by_day = {item["day"]: item["count"] for item in data}

        alarm_daily_count = []
        for i in range(days_count):
            day = start_date + datetime.timedelta(days=i)
            alarm_daily_count.append({
                "day": day.isoformat(),
                "count": counts_by_day.get(day, 0)
            })

        # -------------------------------------------------
        # 4) Energy MWH4 Daily Accumulated (last 7 days)
        # -------------------------------------------------
        energy_mwh4_daily_accumulated = get_energy_mwh4_daily_accumulated(days=7)

        # -------------------------------------------------
        # 5) Low delta-T sites (cached for 24h after first call)
        # -------------------------------------------------
        low_delta_t_sites = get_low_delta_t_sites_cached()

        # -------------------------------------------------
        # Final Response
        # -------------------------------------------------
        return Response({
            "ets_connectivity": ets_connectivity,
            "active_alarms": active_alarms,
            "alarm_daily_count": alarm_daily_count,
            "energy_mwh4_daily_accumulated": energy_mwh4_daily_accumulated,
            "low_delta_t_sites": low_delta_t_sites,
        })

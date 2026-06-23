from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    UserViewSet,
    UserWithDataLoggerCountViewSet,
    me,
    ETSTokenObtainPairView,
    UserSoftDeleteView,
    UserRestoreView,
)
from core.views import (
    ETSSiteViewSet,
    ETSSiteBillingConfigViewSet,
    ETSSiteBillingViewSet,
    ETSConnectivityView,
    DashboardSummaryView,
    ETSSiteSoftDeleteView,
    ETSSiteRestoreView,
    ETSSiteBillingSoftDeleteView,
    ETSSiteBillingRestoreView,

)
from opc.views import (
    OPCSiteBaseAlarmRuleRestoreView,
    OPCSiteBaseAlarmRuleSoftDeleteView,
    OPCSiteObjectsLiveView,
    EnergyMWH4DailyAccumulatedView,
    OPCLastActiveAlarmsView,
    OPCLastAlarmEventsView,
    OPCConnectionViewSet,
    OPCConnectionCreateTestView,
    OPCConnectionTestOnlyView,
    OPCAssetViewSet,
    OPCObjectViewSet,
    OPCNodeViewSet,
    OPCConnectionBrowseView,
    OPCConnectionAutoDiscoverView,
    OPCNodeLiveViewSet,
    OPCNodeHistoryViewSet,
    OPCAlarmRuleViewSet,
    OPCAlarmLiveViewSet,
    OPCAlarmEventViewSet,
    OPCPollingScheduleView,
    OPCPollingRunConnectionView,
    OPCConnectionLatestValuesView,
    OPCNodeValueHistoryView,
    OPCAlarmSeverityCountView,
    OPCSiteNodesHistoryView,
    OPCSiteDashboardView,
    OPCNodeHistoryViewSet2,
    OPCAlarmEventViewSet2,
    OPCHistorianFetchView,
    OPCConnectionSoftDeleteView,
    OPCConnectionRestoreView,
    OPCAlarmRuleSoftDeleteView,
    OPCAlarmRuleRestoreView,
    SiteBillingDataView,
    OPCGeneratedSiteLinkViewSet,
    OPCGeneratedSiteLinkGenerateView,
    OPCGeneratedSiteLinkSoftDeleteView,
    OPCGeneratedSiteLinkRestoreView,
    OPCSiteBaseAlarmRuleViewSet,
    OPCSiteBaseAlarmRuleViewSet2,
    AcknowledgeAlarmView,
)

from django.shortcuts import render

def index(request, path=''):
    if path:
        import os
        from django.conf import settings
        from django.views.static import serve
        full_path = os.path.join(settings.FRONTEND_DIR, path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return serve(request, path, document_root=settings.FRONTEND_DIR)
    return render(request, 'index.html')


router = DefaultRouter()
router.register(r"ets-sites",          ETSSiteViewSet)
router.register(r"ets-billing-config", ETSSiteBillingConfigViewSet)
router.register(r"ets-billing",        ETSSiteBillingViewSet)

router.register(r"opc-connections",    OPCConnectionViewSet)
router.register(r"opc-assets",         OPCAssetViewSet)
router.register(r"opc-objects",        OPCObjectViewSet)
router.register(r"opc-nodes",          OPCNodeViewSet)
router.register(r"opc-live",           OPCNodeLiveViewSet)
router.register(r"opc-history",        OPCNodeHistoryViewSet)
router.register(r"opc-history-all",        OPCNodeHistoryViewSet2,"opc-history-all")

router.register(r"opc-alarm-rules",    OPCAlarmRuleViewSet , "opc-alarm-rules")
router.register(r"opc-alarm-base-rules", OPCSiteBaseAlarmRuleViewSet , "opc-alarm-base-rules")
router.register(r"opc-alarm-base-rules-all", OPCSiteBaseAlarmRuleViewSet2,"opc-alarm-base-rules-all")
router.register(r"opc-alarm-live",     OPCAlarmLiveViewSet)
router.register(r"opc-alarm-events",   OPCAlarmEventViewSet)
router.register(r"opc-alarm-events-all",   OPCAlarmEventViewSet2,"opc-alarm-events-all")


router.register(r"opc-site-links-generate",     OPCGeneratedSiteLinkViewSet,    basename="opc-site-links")

router.register(r"users",              UserViewSet,                    basename="users")
router.register(r"users-summary",      UserWithDataLoggerCountViewSet, basename="users-summary")

urlpatterns = [


    # Admin site
    path("admin/",                                         admin.site.urls),

    # API endpoints
    path("api/",                                           include(router.urls)),

    # Authentication endpoints
    path("api/auth/login/",                                ETSTokenObtainPairView.as_view(),        name="token_obtain_pair"),
    path("api/auth/refresh/",                              TokenRefreshView.as_view(),              name="token_refresh"),
    path("api/auth/me/",                                   me,                                      name="me"),

    # User soft delete / restore
    path("api/users/<int:pk>/soft-delete/",                UserSoftDeleteView.as_view(),            name="user-soft-delete"),
    path("api/users/<int:pk>/restore/",                    UserRestoreView.as_view(),               name="user-restore"),

    # ETS Site soft delete / restore
    path("api/ets-sites/<int:pk>/soft-delete/",            ETSSiteSoftDeleteView.as_view(),         name="ets-site-soft-delete"),
    path("api/ets-sites/<int:pk>/restore/",                ETSSiteRestoreView.as_view(),            name="ets-site-restore"),

    # ETS Site Billing soft delete / restore
    path("api/ets-billing/<int:pk>/soft-delete/",          ETSSiteBillingSoftDeleteView.as_view(),  name="ets-billing-soft-delete"),
    path("api/ets-billing/<int:pk>/restore/",              ETSSiteBillingRestoreView.as_view(),     name="ets-billing-restore"),

    # OPC Connection soft delete / restore
    path("api/opc-connections/<int:pk>/soft-delete/",      OPCConnectionSoftDeleteView.as_view(),   name="opc-connection-soft-delete"),
    path("api/opc-connections/<int:pk>/restore/",          OPCConnectionRestoreView.as_view(),      name="opc-connection-restore"),

    # OPC Alarm Rule soft delete / restore
    path("api/opc-alarm-rules/<int:pk>/soft-delete/",      OPCAlarmRuleSoftDeleteView.as_view(),    name="opc-alarm-rule-soft-delete"),
    path("api/opc-alarm-rules/<int:pk>/restore/",          OPCAlarmRuleRestoreView.as_view(),       name="opc-alarm-rule-restore"),

    # OPC Site Base Alarm Rule soft delete / restore
    path("api/opc-alarm-base-rules/<int:pk>/soft-delete/",  OPCSiteBaseAlarmRuleSoftDeleteView.as_view(), name="opc-alarm-base-rule-soft-delete"),
    path("api/opc-alarm-base-rules/<int:pk>/restore/",      OPCSiteBaseAlarmRuleRestoreView.as_view(),    name="opc-alarm-base-rule-restore"),

    # OPC Generated Site Link — generate + soft delete / restore
    path("api/opc-site-links/generate/",                   OPCGeneratedSiteLinkGenerateView.as_view(), name="opc-site-link-generate"),
    path("api/opc-site-links/<uuid:pk>/soft-delete/",      OPCGeneratedSiteLinkSoftDeleteView.as_view(), name="opc-site-link-soft-delete"),
    path("api/opc-site-links/<uuid:pk>/restore/",          OPCGeneratedSiteLinkRestoreView.as_view(),    name="opc-site-link-restore"),

    #Main Dashboard and analytics endpoints
    path("api/dashboard-summary/",                         DashboardSummaryView.as_view(),          name="dashboard-summary"),
    path("api/ets-connectivity/",                          ETSConnectivityView.as_view(),           name="ets-connectivity"),
    path("api/opc-node-value-history/",                    OPCNodeValueHistoryView.as_view(),       name="opc-node-value-history"),
    path("api/opc-last-active-alarms/",                    OPCLastActiveAlarmsView.as_view(),       name="opc-last-active-alarms"),
    path("api/opc-last-alarm-events/",                     OPCLastAlarmEventsView.as_view(),        name="opc-last-alarm-events"),
    path("api/opc-alarm-severity-count/",                  OPCAlarmSeverityCountView.as_view(),     name="opc-alarm-severity-count"),

    # OPC connection test and browse endpoints
    path("api/opc-connection-create-test/",                OPCConnectionCreateTestView.as_view(),   name="opc-connection-create-test"),
    path("api/opc-connection-test-only/",                  OPCConnectionTestOnlyView.as_view(),      name="opc-connection-test-only"),
    path("api/opc-connection-browse/<int:connection_id>/", OPCConnectionBrowseView.as_view(),       name="opc-connection-browse"),
    path("api/opc-connection-auto-discover/<int:connection_id>/", OPCConnectionAutoDiscoverView.as_view(), name="opc-connection-auto-discover"),
    path("api/opc-connection-latest/<int:connection_id>/", OPCConnectionLatestValuesView.as_view(), name="opc-connection-latest"),
    path("api/opc-polling-schedule/",                      OPCPollingScheduleView.as_view(),        name="opc-polling-schedule"),
    path("api/opc-polling-run/<int:connection_id>/",       OPCPollingRunConnectionView.as_view(),   name="opc-polling-run"),

    # Energy endpoints
    path("api/energy-mwh-4-daily-accumulated/",            EnergyMWH4DailyAccumulatedView.as_view(),name="energy-mwh-4-daily-accumulated"),

    # Site-specific endpoints
    path("api/opc-site-nodes-history/<int:site_id>/",       OPCSiteNodesHistoryView.as_view(),        name="opc-site-nodes-history"),
    path("api/opc-site-live/<int:site_id>/",         OPCSiteObjectsLiveView.as_view(),              name="opc-site-live"),
    path("api/opc-site-dashboard/<int:site_id>/",              OPCSiteDashboardView.as_view(),      name="opc-site-dashboard"),
    path("api/ets-sites/<int:site_id>/billing-data/",  SiteBillingDataView.as_view(),  name="site-billing-data"),


    # Historian fetch (POST — fetches external REST API historian data and stores it)
    path("api/opc-historian-fetch/",                     OPCHistorianFetchView.as_view(),            name="opc-historian-fetch"),

    # Acknowledge active alarm (updates OPCAlarmLive + active OPCAlarmEvent)
    path("api/alarms/<int:alarm_id>/acknowledge/",       AcknowledgeAlarmView.as_view(),             name="acknowledge-alarm"),

    # Flutter Web Catch-all (SPA Routing + Static Files)
    re_path(r'^(?P<path>.*)$', index, name='index'),

]

from django.contrib import admin
from .models import (
    OPCConnection,
    OPCAsset,
    OPCObject,
    OPCNode,
    OPCNodeLive,
    OPCNodeHistory,
    OPCAlarmRule,
    OPCAlarmLive,
    OPCAlarmEvent,
)


@admin.register(OPCConnection)
class OPCConnectionAdmin(admin.ModelAdmin):
    list_display  = ["id", "name", "endpoint_url", "enabled", "is_deleted", "created_at"]
    list_filter   = ["enabled", "is_deleted"]
    search_fields = ["name", "endpoint_url"]
    actions       = ["soft_delete_connections", "restore_connections"]

    def soft_delete_connections(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"{count} connection(s) soft-deleted.")
    soft_delete_connections.short_description = "Soft delete selected connections"

    def restore_connections(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} connection(s) restored.")
    restore_connections.short_description = "Restore selected connections"


@admin.register(OPCAsset)
class OPCAssetAdmin(admin.ModelAdmin):
    list_display  = ["id", "name", "opc_name", "connection", "ets_site", "created_at"]
    list_filter   = ["connection", "ets_site"]
    search_fields = ["name", "opc_name"]


@admin.register(OPCObject)
class OPCObjectAdmin(admin.ModelAdmin):
    list_display  = ["id", "name", "opc_name", "asset", "connection", "created_at"]
    list_filter   = ["connection", "asset"]
    search_fields = ["name", "opc_name"]


@admin.register(OPCNode)
class OPCNodeAdmin(admin.ModelAdmin):
    list_display  = ["id", "name", "opc_name", "data_type", "unit", "object", "created_at"]
    list_filter   = ["data_type", "object"]
    search_fields = ["name", "opc_name", "opc_address"]


@admin.register(OPCNodeLive)
class OPCNodeLiveAdmin(admin.ModelAdmin):
    list_display  = ["node", "value", "status", "source_ts", "updated_at"]
    list_filter   = ["status"]
    search_fields = ["node__name"]


@admin.register(OPCNodeHistory)
class OPCNodeHistoryAdmin(admin.ModelAdmin):
    list_display  = ["id", "node", "value", "status", "source_ts", "created_at"]
    list_filter   = ["status", "node"]
    search_fields = ["node__name"]


@admin.register(OPCAlarmRule)
class OPCAlarmRuleAdmin(admin.ModelAdmin):
    list_display  = ["id", "name", "node", "alarm_type", "severity", "limit_value",
                     "enabled", "is_deleted", "created_at"]
    list_filter   = ["alarm_type", "severity", "enabled", "is_deleted"]
    search_fields = ["name", "node__name"]
    actions       = ["soft_delete_rules", "restore_rules"]

    def soft_delete_rules(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"{count} rule(s) soft-deleted.")
    soft_delete_rules.short_description = "Soft delete selected alarm rules"

    def restore_rules(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} rule(s) restored.")
    restore_rules.short_description = "Restore selected alarm rules"


@admin.register(OPCAlarmLive)
class OPCAlarmLiveAdmin(admin.ModelAdmin):
    list_display  = ["rule", "is_active", "value", "status", "activation_count", "activated_at", "updated_at"]
    list_filter   = ["is_active"]
    search_fields = ["rule__name"]


@admin.register(OPCAlarmEvent)
class OPCAlarmEventAdmin(admin.ModelAdmin):
    list_display  = ["id", "rule", "started_at", "ended_at", "acknowledged", "acknowledged_by"]
    list_filter   = ["acknowledged", "rule"]
    search_fields = ["rule__name"]

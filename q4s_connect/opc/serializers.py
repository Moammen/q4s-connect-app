from rest_framework import serializers
from .models import (
    OPCConnection, OPCAsset, OPCObject, OPCNode, OPCNodeLive, OPCNodeHistory,
    OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent,
    OPCGeneratedSiteLink, OPCSiteBaseAlarmRule
)

class OPCConnectionSerializer(serializers.ModelSerializer):

    class Meta:
        model  = OPCConnection
        fields = "__all__"
        read_only_fields = ["is_deleted"]

    def validate_auth_type(self, value):
        # Normalize frontend variants (e.g. 'username_password') to 'username'
        if value and 'username' in value.lower():
            return 'username'
        return value or 'anonymous'

    def validate_endpoint_url(self, value):
        instance = getattr(self, 'instance', None)
        if not instance or instance.endpoint_url != value:
            if OPCConnection.objects.filter(endpoint_url=value).exists():
                raise serializers.ValidationError(
                    f"An OPC connection with endpoint URL '{value}' already exists."
                )
        return value

class OPCConnectionNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model  = OPCConnection
        fields = ["id", "name", "created_at"]

class OPCAssetSerializer(serializers.ModelSerializer):
    connection_detail = OPCConnectionNestedSerializer(source="connection", read_only=True)
    ets_site_name = serializers.CharField(source="ets_site.name", read_only=True, default=None)

    class Meta:
        model  = OPCAsset
        fields = "__all__"

class OPCAssetNestedSerializer(serializers.ModelSerializer):
    connection_name = serializers.CharField(source="connection.name", read_only=True)
    ets_site_name   = serializers.CharField(source="ets_site.name", read_only=True, default=None)

    class Meta:
        model  = OPCAsset
        fields = ["id", "name", "opc_name", "opc_address", "connection", "connection_name", "ets_site", "ets_site_name", "created_at"]

class OPCObjectSerializer(serializers.ModelSerializer):
    asset_detail      = OPCAssetNestedSerializer(source="asset", read_only=True)
    connection_detail = OPCConnectionNestedSerializer(source="connection", read_only=True)
    class Meta:
        model  = OPCObject
        fields = "__all__"

class OPCObjectNestedSerializer(serializers.ModelSerializer):
    connection_name = serializers.CharField(source="connection.name", read_only=True)
    asset_name      = serializers.CharField(source="asset.name", read_only=True, default=None)
    ets_site_name   = serializers.CharField(source="asset.ets_site.name", read_only=True, default=None)

    class Meta:
        model  = OPCObject
        fields = ["id", "name", "opc_name", "opc_address", "parent_path", "connection", "connection_name", "asset", "asset_name", "ets_site_name", "created_at"]

class OPCNodeSerializer(serializers.ModelSerializer):
    object_detail = OPCObjectNestedSerializer(source="object", read_only=True)
    class Meta:
        model  = OPCNode
        fields = "__all__"

class OPCNodeLiveSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OPCNodeLive
        fields = "__all__"

class OPCNodeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = OPCNodeHistory
        fields = "__all__"

class SiteLiveTagSerializer(serializers.ModelSerializer):
    node_id         = serializers.IntegerField(source="node.id")
    node_name       = serializers.CharField(source="node.name")
    opc_address     = serializers.CharField(source="node.opc_address")
    data_type       = serializers.CharField(source="node.data_type")
    unit            = serializers.CharField(source="node.unit")
    object_name     = serializers.CharField(source="node.object.name")
    asset_name      = serializers.CharField(source="node.object.asset.name", default=None)
    connection_name = serializers.CharField(source="node.object.connection.name")

    class Meta:
        model  = OPCNodeLive
        fields = [
            "node_id", "node_name", "opc_address", "data_type", "unit",
            "object_name", "asset_name", "connection_name",
            "value", "actual_value", "actual_timestamp",
            "status", "source_ts", "server_ts", "updated_at",
        ]

class OPCAlarmRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OPCAlarmRule
        fields = "__all__"
        read_only_fields = ["is_deleted"]

class OPCSiteBaseAlarmRuleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True, default=None)
    updated_by = serializers.CharField(source="updated_by.username", read_only=True, default=None)
    deleted_by = serializers.CharField(source="deleted_by.username", read_only=True, default=None)
    class Meta:
        model  = OPCSiteBaseAlarmRule
        fields = ["id","created_by", "updated_by", "deleted_by",
                  "node","name", "alarm_type", "severity","deadband","enabled", "limit_value",
                    "created_at", "updated_at", "is_deleted"
                  ]
        read_only_fields = ["is_deleted"]
class OPCAlarmRuleNestedSerializer(serializers.ModelSerializer):
    node_name       = serializers.CharField(source="node.name", read_only=True)
    object_name     = serializers.CharField(source="node.object.name", read_only=True)
    asset_name      = serializers.CharField(source="node.object.asset.name", read_only=True, default=None)
    connection_name = serializers.CharField(source="node.object.connection.name", read_only=True)
    site_name       = serializers.CharField(source="node.object.asset.ets_site.name", read_only=True, default=None)
    
    class Meta:
        model  = OPCAlarmRule
        fields = [
             "name", "alarm_type", "severity", "limit_value",
            "node_name", "object_name", "asset_name", "connection_name", "site_name",
        ]

class OPCAlarmLiveSerializer(serializers.ModelSerializer):
    rule_detail = OPCAlarmRuleNestedSerializer(source="rule", read_only=True)

    class Meta:
        model  = OPCAlarmLive
        fields = [
            "rule", "rule_detail",
            "is_active", "value", "status", "message",
            "activation_count", "activated_at", "cleared_at", "updated_at",
        ]

class OPCAlarmEventSerializer(serializers.ModelSerializer):
    rule_detail = OPCAlarmRuleNestedSerializer(source="rule", read_only=True)

    class Meta:
        model  = OPCAlarmEvent
        fields = [
            "id", "rule", "rule_detail",
            "started_at", "ended_at",
            "start_value", "end_value",
            "start_status", "end_status",
            "message", "acknowledged", "acknowledged_at", "acknowledged_by",
            "created_at",
        ]

class OPCGeneratedSiteLinkSerializer(serializers.ModelSerializer):
    site_name           = serializers.CharField(source="site.name",           read_only=True, default=None)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    updated_by_username = serializers.CharField(source="updated_by.username", read_only=True, default=None)

    class Meta:
        model  = OPCGeneratedSiteLink
        fields = [
            "id",
            "site", "site_name",
            "url",
            "username",
            "json_data",
            "is_active", "is_deleted",
            "expire_date", "filter_start_date", "filter_end_date",
            "last_synced_at",
            "created_at", "created_by", "created_by_username",
            "updated_at", "updated_by", "updated_by_username",
        ]
        # password_hash intentionally omitted — never exposed via the API
        read_only_fields = [
            "id", "url",
            "is_deleted",
            "json_data",        # only the generate view writes this
            "last_synced_at",   # set by the Flask sync (later)
            "created_at", "created_by", "created_by_username",
            "updated_at", "updated_by", "updated_by_username",
        ]

import uuid
from django.db import models
from core.models import ETSSite

class OPCConnection(models.Model):
    name         = models.CharField(max_length=255)
    endpoint_url = models.TextField(unique=True)
    enabled      = models.BooleanField(default=True)

    security_policy = models.CharField(max_length=50, blank=True, null=True)
    security_mode   = models.CharField(max_length=30, blank=True, null=True)

    auth_type = models.CharField(max_length=30, default="anonymous")
    username  = models.CharField(max_length=255, blank=True, null=True)
    password  = models.CharField(max_length=255, blank=True, null=True)

    client_cert_path = models.TextField(blank=True, null=True)
    client_key_path  = models.TextField(blank=True, null=True)
    server_cert_path = models.TextField(blank=True, null=True)

    timeout_seconds  = models.PositiveIntegerField(default=10)
    polling_rate_ms  = models.PositiveIntegerField(default=1000)
    last_polled_at   = models.DateTimeField(blank=True, null=True)

    last_error_code    = models.CharField(max_length=50, blank=True, null=True)
    last_error_message = models.TextField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    is_deleted         = models.BooleanField(default=False)

class OPCAsset(models.Model):
    connection  = models.ForeignKey(OPCConnection, on_delete=models.CASCADE, related_name="assets")
    ets_site    = models.ForeignKey(ETSSite, on_delete=models.SET_NULL, related_name="opc_assets", null=True, blank=True)
    name        = models.CharField(max_length=255)
    opc_name    = models.CharField(max_length=255)
    opc_address = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('connection', 'opc_name')

    def __str__(self):
        return f"{self.name} ({self.connection.name})"

class OPCObject(models.Model):
    connection  = models.ForeignKey(OPCConnection, on_delete=models.CASCADE, null=True, blank=True)
    asset       = models.ForeignKey(OPCAsset, on_delete=models.CASCADE, null=True, blank=True, related_name="opc_objects")
    name        = models.CharField(max_length=255)
    opc_name    = models.CharField(max_length=255)
    opc_address = models.TextField(blank=True, null=True)
    parent_path = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('connection', 'opc_name')

class OPCNode(models.Model):

    object      = models.ForeignKey(OPCObject, on_delete=models.CASCADE)
    name        = models.CharField(max_length=255)
    opc_name    = models.CharField(max_length=255)
    opc_address = models.TextField()
    data_type   = models.CharField(max_length=50, null=True, blank=True)
    unit        = models.CharField(max_length=50, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

class OPCNodeLive(models.Model):
    node       = models.OneToOneField(OPCNode, on_delete=models.CASCADE, primary_key=True)
    value      = models.JSONField(null=True, blank=True)
    actual_value = models.FloatField(null=True, blank=True)
    actual_timestamp = models.DateTimeField(null=True, blank=True)
    status     = models.CharField(max_length=50, null=True)
    source_ts  = models.DateTimeField(null=True)
    server_ts  = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class OPCNodeHistory(models.Model):
    node       = models.ForeignKey(OPCNode, on_delete=models.CASCADE)
    value      = models.JSONField(null=True, blank=True)
    actual_value = models.FloatField(null=True, blank=True)
    actual_timestamp = models.DateTimeField(null=True, blank=True)
    status     = models.CharField(max_length=50, null=True)
    source_ts  = models.DateTimeField(null=True)
    server_ts  = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["node", "-source_ts"]),
        ]

class OPCAlarmRule(models.Model):
    ALARM_TYPE_CHOICES = [
        ("high",       "High Limit"),
        ("low",        "Low Limit"),
        ("high_high",  "High High Limit"),
        ("low_low",    "Low Low Limit")
        
    ]
    SEVERITY_CHOICES = [
        ("low",      "Low"),
        ("medium",   "Medium"),
        ("high",     "High"),
        ("critical", "Critical"),
    ]

    node        = models.ForeignKey("OPCNode", on_delete=models.CASCADE, related_name="alarm_rules")
    name        = models.CharField(max_length=255)
    alarm_type  = models.CharField(max_length=50,  choices=ALARM_TYPE_CHOICES)
    limit_value = models.FloatField(null=True, blank=True)
    deadband    = models.FloatField(default=0)
    severity    = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    enabled     = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    is_deleted  = models.BooleanField(default=False)

    class Meta:
        unique_together = ("node", "name")

    def __str__(self):
        return f"{self.node.name} - {self.name}"

class OPCSiteBaseAlarmRule(models.Model):
    ALARM_TYPE_CHOICES = [
        ("high",       "High Limit"),
        ("low",        "Low Limit"),
        ("high_high",  "High High Limit"),
        ("low_low",    "Low Low Limit")
        
    ]
    SEVERITY_CHOICES = [
        ("low",      "Low"),
        ("medium",   "Medium"),
        ("high",     "High"),
        ("critical", "Critical"),
    ]
    NODE_CHOICES = [
        ("flow_m3h_1",      "Flow (m³/h)"),
        ("temp_supply_c_2", "Supply Temp (°C)"),
        ("temp_return_c_3", "Return Temp (°C)"),
        ("energy_mwh_4",    "Energy (MWh)"),
        ("power_kw_5",      "Power (kW)"),
        ("volume_m3_6",     "Volume (m³)"),
        ("temp_diff_k_7",   "Temp Diff (K)"),
        ("serial_8",        "Serial"),
        ("address_9",       "Address"),
    ]

    node        = models.CharField(max_length=60, choices=NODE_CHOICES, null=False, blank=False)
    name        = models.CharField(max_length=255)
    alarm_type  = models.CharField(max_length=50,  choices=ALARM_TYPE_CHOICES)
    limit_value = models.FloatField(null=True, blank=True)
    deadband    = models.FloatField(default=0)
    severity    = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    enabled     = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    created_by  = models.ForeignKey("accounts.User",null=True,blank=True,on_delete=models.SET_NULL,related_name="created_site_base_alarm_rules",)
    updated_by  = models.ForeignKey("accounts.User",null=True,blank=True,on_delete=models.SET_NULL,related_name="updated_site_base_alarm_rules",)
    deleted_by  = models.ForeignKey("accounts.User",null=True,blank=True,on_delete=models.SET_NULL,related_name="deleted_site_base_alarm_rules",)   
    is_deleted  = models.BooleanField(default=False)
    class Meta:
        unique_together = ("node", "name")

    def __str__(self):
        return f"{self.node.name} - {self.name}"

class OPCAlarmLive(models.Model):
    rule             = models.OneToOneField(OPCAlarmRule, on_delete=models.CASCADE, primary_key=True, related_name="live_alarm")
    is_active        = models.BooleanField(default=False)
    value            = models.FloatField(null=True, blank=True)
    status           = models.CharField(max_length=50, null=True, blank=True)
    message          = models.TextField(blank=True, null=True)
    activation_count = models.PositiveIntegerField(default=0)
    activated_at     = models.DateTimeField(null=True, blank=True)
    cleared_at       = models.DateTimeField(null=True, blank=True)
    updated_at       = models.DateTimeField(auto_now=True)

    acknowledged     = models.BooleanField(default=False)
    acknowledged_at  = models.DateTimeField(null=True, blank=True)
    acknowledged_by  = models.ForeignKey(
        "accounts.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="acknowledged_live_alarms",
    )

    def __str__(self):
        state = "Active" if self.is_active else "Clear"
        return f"{self.rule.name} - {state}"

class OPCAlarmEvent(models.Model):
    rule             = models.ForeignKey(OPCAlarmRule, on_delete=models.CASCADE, related_name="events")
    started_at       = models.DateTimeField()
    ended_at         = models.DateTimeField(null=True, blank=True)
    start_value      = models.FloatField(null=True, blank=True)
    end_value        = models.FloatField(null=True, blank=True)
    start_status     = models.CharField(max_length=50, null=True, blank=True)
    end_status       = models.CharField(max_length=50, null=True, blank=True)
    message          = models.TextField(blank=True, null=True)
    acknowledged     = models.BooleanField(default=False)
    acknowledged_at  = models.DateTimeField(null=True, blank=True)
    acknowledged_by  = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["rule", "-started_at"]),
            models.Index(fields=["ended_at"]),
        ]

    def __str__(self):
        return f"{self.rule.name} from {self.started_at}"


class OPCGeneratedSiteLink(models.Model):

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(
        ETSSite,
        on_delete=models.CASCADE,
        related_name="generated_site_links",
    )

    url       = models.TextField()
    json_data = models.JSONField(null=True, blank=True)

    # ── Credentials (set at generate time; password_hash is a hash, never plaintext) ──
    username       = models.CharField(max_length=64, blank=True, default="")
    password_hash  = models.CharField(max_length=128, blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)

    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    expire_date       = models.DateTimeField()
    filter_start_date = models.DateTimeField()
    filter_end_date   = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_site_links",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_site_links",
    )

    class Meta:
        indexes = [
            models.Index(fields=["site", "-created_at"]),
            models.Index(fields=["expire_date"]),
        ]

    def __str__(self):
        return f"SiteLink({self.site_id}) — {self.id}"

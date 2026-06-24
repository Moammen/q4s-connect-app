from django.db import models


class ETSSite(models.Model):

    REGION_CHOICES = [
        ("dubai", "Dubai"),
        ("northern_region", "Northern Region"),
        ("abu_dhabi", "Abu Dhabi"),
    ]

    COUNTRY_CHOICES = [
        ("UAE", "United Arab Emirates"),
    ]

    ALARM_STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name               = models.CharField(max_length=200, unique=True)
    ets_code           = models.CharField(max_length=100, unique=True, blank=True, null=True)
    ets_name           = models.CharField(max_length=200, blank=True, null=True)
    plot_number        = models.CharField(max_length=100, blank=True, null=True)
    location           = models.CharField(max_length=255, blank=True, null=True)
    latitude           = models.FloatField()
    longitude          = models.FloatField()
    region             = models.CharField(max_length=30, choices=REGION_CHOICES, blank=True, null=True)
    country            = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default="UAE")
    contract_number    = models.CharField(max_length=100, blank=True, null=True)
    contract_document  = models.FileField(upload_to="billing_contracts/", blank=True, null=True)
    customer_name      = models.CharField(max_length=200, blank=True, null=True)

    declared_load      = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    declared_load_fee  = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    contracted_delta_t = models.DecimalField(max_digits=8,  decimal_places=2, blank=True, null=True)

    connected          = models.BooleanField(default=False)
    active             = models.BooleanField(default=True)
    alarm_status       = models.CharField(max_length=10, choices=ALARM_STATUS_CHOICES, default="inactive")

    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)
    is_deleted         = models.BooleanField(default=False)

    class Meta:
        db_table     = "core_ets_site"
        verbose_name = "ETS Site"

    def __str__(self):
        return self.name

class ETSSiteBillingConfig(models.Model):

    ets_site             = models.OneToOneField(ETSSite, on_delete=models.CASCADE, related_name="billing_config")

    delta_t_tolerance    = models.DecimalField(max_digits=8,  decimal_places=2,default=0.00, blank=True, null=True)
    
    delta_t_fee_rate     = models.DecimalField(max_digits=5, decimal_places=4,default=0.10, blank=True, null=True)

    consumption_fee_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    other_fees           = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, blank=True, null=True)

    billing_day          = models.PositiveSmallIntegerField(
                               blank=True, null=True,
                               choices=[(d, d) for d in range(1, 29)],
                               help_text="Day of the month billing cycle starts (1–28)"
                           )
    
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)



    class Meta:
        db_table     = "core_ets_site_billing_config"
        verbose_name = "ETS Site Billing Config"

    def __str__(self):
        return f"{self.ets_site.name} - billing config"

class ETSSiteBilling(models.Model):

    ets_site        = models.ForeignKey(ETSSite, on_delete=models.CASCADE, related_name="billings")
    from_date       = models.DateField()
    to_date         = models.DateField()
    billing_date    = models.DateField(blank=True, null=True)
    average_delta_t = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    delta_t_fees    = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    consumption     = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    consumption_fee = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    declared_load_fee = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    total             = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    is_deleted         = models.BooleanField(default=False)

    class Meta:
        db_table = "core_ets_site_billing"
        ordering = ["-from_date"]
        indexes  = [
            models.Index(fields=["ets_site", "from_date", "to_date"]),
        ]
        verbose_name = "ETS Site Billing"

    def __str__(self):
        return f"{self.ets_site.name} billing {self.from_date} to {self.to_date}"


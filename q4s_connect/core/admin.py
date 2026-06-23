from django.contrib import admin
from django.db import transaction
from .models import ETSSite, ETSSiteBillingConfig, ETSSiteBilling
from opc.models import OPCAsset


@admin.register(ETSSite)
class ETSSiteAdmin(admin.ModelAdmin):
    list_display  = ("id", "name", "ets_code", "region", "connected", "active",
                     "alarm_status", "is_deleted")
    list_filter   = ("region", "country", "connected", "active", "alarm_status",
                     "is_deleted")
    search_fields = ("name", "ets_code", "cts_name", "customer_name", "location")

    actions = ["soft_delete_sites", "restore_sites"]

    def soft_delete_sites(self, request, queryset):
        # Mirror hard-delete behavior: null out OPCAsset.ets_site for affected sites
        with transaction.atomic():
            site_ids = list(queryset.values_list("id", flat=True))
            unlinked = OPCAsset.objects.filter(ets_site_id__in=site_ids).update(ets_site=None)
            count    = queryset.update(is_deleted=True)
        self.message_user(
            request,
            f"{count} site(s) soft-deleted; {unlinked} asset link(s) cleared."
        )
    soft_delete_sites.short_description = "Soft delete selected sites"

    def restore_sites(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} site(s) restored.")
    restore_sites.short_description = "Restore selected sites"


@admin.register(ETSSiteBillingConfig)
class ETSSiteBillingConfigAdmin(admin.ModelAdmin):
    list_display  = ("id", "ets_site", "billing_day", "delta_t_tolerance",
                     "delta_t_fee_rate", "consumption_fee_rate")
    search_fields = ("ets_site__name",)


@admin.register(ETSSiteBilling)
class ETSSiteBillingAdmin(admin.ModelAdmin):
    list_display  = ("id", "ets_site", "from_date", "to_date", "average_delta_t",
                     "consumption", "is_deleted")
    list_filter   = ("ets_site", "is_deleted")
    search_fields = ("ets_site__name",)

    actions = ["soft_delete_billings", "restore_billings"]

    def soft_delete_billings(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"{count} billing(s) soft-deleted.")
    soft_delete_billings.short_description = "Soft delete selected billings"

    def restore_billings(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} billing(s) restored.")
    restore_billings.short_description = "Restore selected billings"

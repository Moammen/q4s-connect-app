from django.db import models

# Create your models here.

class OPCGeneratedSiteLink(models.Model):

    id = models.CharField(max_length=64, primary_key=True)  # UUID or similar unique identifier
    site = models.IntegerField(null=True,blank=True)

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


    class Meta:
        indexes = [
            models.Index(fields=["site", "-created_at"]),
            models.Index(fields=["expire_date"]),
        ]

    def __str__(self):
        return f"SiteLink({self.site_id}) — {self.id}"

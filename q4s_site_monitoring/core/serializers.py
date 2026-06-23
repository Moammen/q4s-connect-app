from rest_framework import serializers
from .models import (
    OPCGeneratedSiteLink,
)

class OPCGeneratedSiteLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = OPCGeneratedSiteLink
        fields = "__all__"
        extra_kwargs = {
            "password_hash": {"write_only": True},
            "json_data": {"write_only": True},
        }
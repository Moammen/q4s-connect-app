from rest_framework import serializers
from .models import ETSSite, ETSSiteBillingConfig, ETSSiteBilling

VALID_REGIONS   = ["dubai", "northern_region", "abu_dhabi"]
VALID_COUNTRIES = ["UAE"]
VALID_ALARM     = ["active", "inactive"]


class ETSSiteBillingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ETSSiteBillingConfig
        fields = "__all__"


class ETSSiteSerializer(serializers.ModelSerializer):

    billing_config = ETSSiteBillingConfigSerializer( read_only=True)

    class Meta:
        model  = ETSSite
        fields = "__all__"
        read_only_fields = ["is_deleted"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters.")
        qs = ETSSite.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An ETS site with this name already exists.")
        return value

    def validate_ets_code(self, value):
        if value:
            value = value.strip().upper()
            qs = ETSSite.objects.filter(ets_code=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("This ETS code is already used.")
        return value

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate_region(self, value):
        if value and value not in VALID_REGIONS:
            raise serializers.ValidationError(f"Region must be one of: {', '.join(VALID_REGIONS)}.")
        return value

    def validate_country(self, value):
        if value not in VALID_COUNTRIES:
            raise serializers.ValidationError(f"Country must be one of: {', '.join(VALID_COUNTRIES)}.")
        return value

    def validate_alarm_status(self, value):
        if value not in VALID_ALARM:
            raise serializers.ValidationError(f"Alarm status must be one of: {', '.join(VALID_ALARM)}.")
        return value


class ETSSiteBillingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ETSSiteBilling
        fields = "__all__"
        read_only_fields = ["is_deleted"]

    def validate(self, attrs):
        if attrs.get("from_date") and attrs.get("to_date"):
            if attrs["from_date"] > attrs["to_date"]:
                raise serializers.ValidationError({"to_date": "to_date must be after from_date."})
        return attrs


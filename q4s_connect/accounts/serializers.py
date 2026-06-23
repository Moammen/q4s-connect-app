from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
from core.models import ETSSite
from core.serializers import ETSSiteSerializer

VALID_ROLES = ["engineer", "admin", "operator", "user"]


class UserSerializer(serializers.ModelSerializer):
    ets_sites    = ETSSiteSerializer(many=True, read_only=True)
    ets_site_ids = serializers.PrimaryKeyRelatedField(
        queryset=ETSSite.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="ets_sites"
    )
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "all_sites", "password", "ets_sites", "ets_site_ids",
            "is_deleted",
        ]
        read_only_fields = ["is_deleted"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Hide soft-deleted sites from the user's site list
        if instance.all_sites:
            ret["ets_sites"] = ETSSiteSerializer(
                ETSSite.objects.filter(is_deleted=False), many=True
            ).data
        else:
            ret["ets_sites"] = ETSSiteSerializer(
                instance.ets_sites.filter(is_deleted=False), many=True
            ).data
        return ret

    def validate_username(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters.")
        if " " in value:
            raise serializers.ValidationError("Username cannot contain spaces.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return value

    def validate_role(self, value):
        if value not in VALID_ROLES:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(VALID_ROLES)}.")
        return value

    def validate_email(self, value):
        if value:
            value = value.strip().lower()
            if User.objects.filter(email=value).exclude(
                pk=self.instance.pk if self.instance else None
            ).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        password  = validated_data.pop("password")
        ets_sites = validated_data.pop("ets_sites", [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.ets_sites.set(ets_sites)
        return user

    def update(self, instance, validated_data):
        password  = validated_data.pop("password", None)
        ets_sites = validated_data.pop("ets_sites", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if ets_sites is not None:
            instance.ets_sites.set(ets_sites)
        instance.save()
        return instance


class UserWithLoggerCountSerializer(serializers.ModelSerializer):
    ets_site_count = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "all_sites", "ets_site_count",
            "is_deleted",
        ]
        read_only_fields = ["is_deleted"]

    def get_ets_site_count(self, obj):
        if obj.all_sites:
            return ETSSite.objects.count()
        return obj.ets_sites.count()


class ETSTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT login serializer that blocks soft-deleted users from logging in.
    Raises AuthenticationFailed with a clear message instead of issuing tokens.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        if getattr(self.user, "is_deleted", False):
            raise AuthenticationFailed(
                "This user account has been deleted.",
                code="user_deleted",
            )
        return data

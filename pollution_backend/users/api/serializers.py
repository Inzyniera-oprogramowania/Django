from django.contrib.auth import get_user_model
from django.db import transaction
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from pollution_backend.users.models import AdvancedUser
from pollution_backend.users.models import Institution
from pollution_backend.users.models import Resident
from ..models import ApiKey

User = get_user_model()


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "type",
            "registration_number",
            "area_of_operation",
            "h3_cells",
        ]


class AdvancedUserSerializer(serializers.ModelSerializer):
    institution = InstitutionSerializer(read_only=True)

    class Meta:
        model = AdvancedUser
        fields = ["id", "institution", "specialization", "employment_date"]


class ResidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resident
        fields = ["id", "h3_index", "city"]


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
            "user_type",
            "profile",
        ]

    def get_user_type(self, obj):
        if hasattr(obj, "resident_profile"):
            return "resident"
        if hasattr(obj, "advanced_profile"):
            return "advanced"
        if obj.is_staff:
            return "admin"
        return "unknown"

    def get_profile(self, obj):
        if hasattr(obj, "resident_profile"):
            return ResidentSerializer(obj.resident_profile).data
        if hasattr(obj, "advanced_profile"):
            return AdvancedUserSerializer(obj.advanced_profile).data
        return None


class CustomRegisterSerializer(RegisterSerializer):
    username = None
    user_type = serializers.ChoiceField(choices=[("resident", "Resident"), ("advanced", "Advanced")])
    city = serializers.CharField(required=False, allow_blank=True)
    institution_id = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(),
        required=False,
        allow_null=True,
    )
    specialization = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        user_type = data.get("user_type")
        if user_type == "advanced":
            if not data.get("institution_id"):
                raise serializers.ValidationError({"institution_id": "This field is required for advanced users."})
        return super().validate(data)

    @transaction.atomic
    def save(self, request):
        user = super().save(request)
        user_type = self.validated_data.get("user_type")

        if user_type == "resident":
            Resident.objects.create(
                user=user,
                city=self.validated_data.get("city"),
            )
        elif user_type == "advanced":
            AdvancedUser.objects.create(
                user=user,
                institution=self.validated_data.get("institution_id"),
                specialization=self.validated_data.get("specialization"),
            )
        return user

class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ['id', 'label', 'key', 'station', 'created_at', 'expires_at', 'is_active', 'request_count', 'limit']
        read_only_fields = ['key', 'created_at', 'expires_at', 'limit']
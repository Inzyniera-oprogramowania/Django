import sys

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.gis.db import models as geomodels
from django.db import models
from django.utils import timezone

TESTING = "pytest" in sys.modules


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            msg = "The Email field must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = '"User"'

    def __str__(self):
        return self.email


class Institution(models.Model):
    name = models.CharField(unique=True, max_length=255)
    type = models.CharField(max_length=50)
    registration_number = models.CharField(unique=True, max_length=50)
    area_of_operation = geomodels.PolygonField(blank=True, null=True, srid=4326)
    h3_cells = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "institution"

    def __str__(self):
        return self.name


class AdvancedUser(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="advanced_profile",
        db_column="userid",
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="institutionid",
    )
    specialization = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    employment_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "advanceduser"

    def __str__(self):
        return f"Expert: {self.user.email}"


class Resident(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="resident_profile",
        db_column="userid",
    )
    home_location = geomodels.PointField(blank=True, null=True, srid=4326)
    h3_index = models.CharField(max_length=15, blank=True, null=True)  # noqa: DJ001
    city = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001

    class Meta:
        db_table = "resident"

    def __str__(self):
        return f"Resident: {self.user.email}"

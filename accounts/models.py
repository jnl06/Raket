import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def resume_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"resumes/user_{instance.user_id}/{uuid.uuid4().hex}{ext}"


class Profile(models.Model):
    """Extra account data. Sign-up screen: role, full name, phone number."""

    class Role(models.TextChoices):
        SEEKER = "job_seeker", "Job Seeker"
        PROVIDER = "job_provider", "Job Provider"

    class Availability(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        ONE_TIME = "one_time", "One-time"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SEEKER)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=300, blank=True, help_text="Comma separated")
    # Employment types the worker is open to (shown as tags on applicant cards).
    availability = models.JSONField(default=list, blank=True)
    resume = models.FileField(upload_to=resume_upload_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def is_provider(self):
        return self.role == self.Role.PROVIDER

    @property
    def is_seeker(self):
        return self.role == self.Role.SEEKER


def get_profile(user):
    """Return the user's profile, creating one lazily (e.g. for createsuperuser accounts)."""
    try:
        return user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=user,
            full_name=user.get_full_name() or user.get_username(),
            role=Profile.Role.PROVIDER if user.is_superuser else Profile.Role.SEEKER,
        )
        return profile


def display_name(user):
    """Public display name for a user (None-safe)."""
    if user is None:
        return "Household"
    try:
        return user.profile.full_name or user.get_username()
    except Profile.DoesNotExist:
        return user.get_full_name() or user.get_username()

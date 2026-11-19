from django.conf import settings
from django.db import models


class Job(models.Model):
    class Category(models.TextChoices):
        HOUSE_CLEANING = "house_cleaning", "House cleaning"
        BABYSITTER = "babysitter", "Babysitter"
        COOK = "cook_kitchen_helper", "Cook/kitchen helper"
        LAUNDRY = "laundry", "Laundry"
        GARDENING = "gardening", "Gardening"
        DRIVER = "driver_delivery", "Driver/delivery"
        ERRANDS = "errands", "Errands"
        REPAIRS = "repairs", "Repairs/handyman"
        OTHER = "other", "Other"

    class Schedule(models.TextChoices):
        MORNING = "morning", "Morning (6 AM - 12 PM)"
        AFTERNOON = "afternoon", "Afternoon (12 PM - 6 PM)"
        EVENING = "evening", "Evening (6 PM - 10 PM)"
        WHOLE_DAY = "whole_day", "Whole day"
        FLEXIBLE = "flexible", "Flexible"

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_jobs",
    )
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField()
    location = models.CharField(max_length=150)
    work_date = models.DateField()
    work_schedule = models.CharField(max_length=20, choices=Schedule.choices)
    estimated_payment = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Pesos"
    )
    number_of_workers = models.PositiveSmallIntegerField(default=1)
    requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.location})"

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import display_name


def _peso(value):
    """500.00 -> '500', 1250.5 -> '1,250.50'."""
    value = Decimal(value)
    if value == value.to_integral_value():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


class JobQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=Job.Status.ACTIVE)

    def upcoming(self):
        """Jobs whose work date hasn't passed yet (in the site's time zone)."""
        return self.filter(work_date__gte=timezone.localdate())

    def open_for_applicants(self):
        """What the public sees: active and not yet past."""
        return self.active().upcoming()

    def with_counts(self):
        """Annotate applicant_count and hired_count (used by the API and the pages)."""
        return self.annotate(
            applicant_count=Count("applications", distinct=True),
            hired_count=Count(
                "applications",
                filter=Q(applications__status="hired"),
                distinct=True,
            ),
        )


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

    class Employment(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        ONE_TIME = "one_time", "One-time"

    class Duration(models.TextChoices):
        ONE_DAY = "one_day", "1 day"
        FEW_DAYS = "few_days", "2-6 days"
        ONE_TWO_WEEKS = "one_two_weeks", "1-2 weeks"
        UP_TO_MONTH = "up_to_month", "Up to 1 month"
        ONGOING = "ongoing", "Ongoing"

    class PayPeriod(models.TextChoices):
        DAY = "day", "Day"
        HOUR = "hour", "Hour"
        JOB = "job", "Whole job"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

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
    employment_type = models.CharField(max_length=20, choices=Employment.choices)
    duration = models.CharField(max_length=20, choices=Duration.choices)
    estimated_payment = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Pesos"
    )
    max_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Upper end of a pay range (e.g. 500 - 900 a day). Optional.",
    )
    pay_period = models.CharField(max_length=10, choices=PayPeriod.choices)
    number_of_workers = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    requirements = models.TextField(
        blank=True, help_text="One qualification per line (shown as bullets)."
    )
    experience = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=150, blank=True)
    how_to_apply = models.TextField(blank=True)
    # Lifecycle state, not job content: every post starts open to applicants.
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.location})"

    # -- display helpers (used by the server-rendered pages) ------------------

    @property
    def household_name(self):
        return display_name(self.posted_by)

    @property
    def payment_amount(self):
        """'₱500' or '₱500 - 900' (when a max is set)."""
        text = f"₱{_peso(self.estimated_payment)}"
        if self.max_payment is not None:
            text += f" - {_peso(self.max_payment)}"
        return text

    @property
    def payment_phrase(self):
        """'₱500 - 900 a day' / 'an hour' / 'for the whole job'."""
        phrase = {"day": "a day", "hour": "an hour", "job": "for the whole job"}[
            self.pay_period
        ]
        return f"{self.payment_amount} {phrase}"

    @property
    def qualifications(self):
        return [
            line.strip(" -•\t") for line in self.requirements.splitlines() if line.strip()
        ]

    @property
    def is_open(self):
        return self.status == self.Status.ACTIVE and self.work_date >= timezone.localdate()


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Not selected"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    cover_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "applicant"], name="unique_application_per_job"
            )
        ]

    def __str__(self):
        return f"{self.applicant} -> {self.job} ({self.status})"

from django.contrib import admin

from .models import Application, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "location",
        "employment_type",
        "work_date",
        "estimated_payment",
        "pay_period",
        "status",
        "posted_by",
        "created_at",
    )
    list_filter = ("status", "category", "employment_type", "duration", "work_schedule", "work_date")
    search_fields = ("title", "location", "description", "industry")
    list_select_related = ("posted_by",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("applicant__email", "job__title")
    list_select_related = ("applicant", "job")

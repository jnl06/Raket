from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "location", "work_date", "estimated_payment", "created_at")
    list_filter = ("category", "work_schedule", "work_date")
    search_fields = ("title", "location", "description")
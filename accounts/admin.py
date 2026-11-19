from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "role", "phone", "location", "created_at")
    list_filter = ("role",)
    search_fields = ("full_name", "user__email", "phone")

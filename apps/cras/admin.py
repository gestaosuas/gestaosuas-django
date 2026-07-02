from django.contrib import admin
from .models import CrasReport


@admin.register(CrasReport)
class CrasReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "unit_name", "month", "year", "updated_at")
    list_filter = ("directorate", "year", "month", "unit_name")
    search_fields = ("unit_name",)

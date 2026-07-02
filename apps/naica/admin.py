from django.contrib import admin
from .models import NaicaReport


@admin.register(NaicaReport)
class NaicaReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "unit_name", "month", "year", "status")
    list_filter = ("directorate", "status", "year", "month")

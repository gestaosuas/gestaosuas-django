from django.contrib import admin

from .models import GenericMonitoringReport






@admin.register(GenericMonitoringReport)
class GenericMonitoringReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "reference", "month", "year", "status")
    list_filter = ("reference", "status", "year", "month")

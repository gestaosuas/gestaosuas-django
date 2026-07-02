from django.contrib import admin
from .models import SineReport, QualificacaoReport


@admin.register(SineReport)
class SineReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "month", "year", "updated_at")
    list_filter = ("year", "month", "directorate")


@admin.register(QualificacaoReport)
class QualificacaoReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "month", "year", "updated_at")
    list_filter = ("year", "month", "directorate")

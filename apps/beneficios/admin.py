from django.contrib import admin
from .models import BeneficiosReport


@admin.register(BeneficiosReport)
class BeneficiosReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "month", "year", "updated_at")
    list_filter = ("year", "month", "directorate")
    search_fields = ("directorate__name",)

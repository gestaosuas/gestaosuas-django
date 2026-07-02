from django.contrib import admin

from .models import DailyReport, Directorate, FormDelegation, MonthlyReport, MonthlySubmission, Osc, Visit, WorkPlan


@admin.register(Directorate)
class DirectorateAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(MonthlySubmission)
class MonthlySubmissionAdmin(admin.ModelAdmin):
    list_display = ("directorate", "month", "year", "user_id", "created_at")
    list_filter = ("directorate", "year", "month")


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "date", "report_type", "user_id")
    list_filter = ("directorate", "date")


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ("directorate", "setor", "month", "year", "status")
    list_filter = ("directorate", "status", "year")


@admin.register(Osc)
class OscAdmin(admin.ModelAdmin):
    list_display = ("name", "directorate", "activity_type", "subsidized_count")
    list_filter = ("directorate",)
    search_fields = ("name", "activity_type", "neighborhood")


@admin.register(WorkPlan)
class WorkPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "osc", "directorate", "status", "updated_at")
    list_filter = ("directorate", "status")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("osc", "directorate", "visit_date", "visit_time", "status")
    list_filter = ("directorate", "status", "visit_date")


@admin.register(FormDelegation)
class FormDelegationAdmin(admin.ModelAdmin):
    list_display = ("visit", "user_id", "delegated_by", "directorate", "created_at")

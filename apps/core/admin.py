from django.contrib import admin

from .models import ActivityLog, MapCategory, MapUnit, SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")
    search_fields = ("key", "value")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action_type", "resource_type", "resource_name", "user_name", "created_at")
    list_filter = ("action_type", "resource_type", "created_at")
    search_fields = ("resource_name", "user_name", "directorate_name")


@admin.register(MapCategory)
class MapCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "created_at")


@admin.register(MapUnit)
class MapUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "region", "phone")
    list_filter = ("category", "region")
    search_fields = ("name", "address", "region")

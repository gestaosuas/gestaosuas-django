from django.contrib import admin

from .models import Profile, ProfileDirectorate


class ProfileDirectorateInline(admin.TabularInline):
    model = ProfileDirectorate
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "primary_directorate")
    list_filter = ("role", "primary_directorate")
    search_fields = ("full_name",)
    inlines = [ProfileDirectorateInline]


@admin.register(ProfileDirectorate)
class ProfileDirectorateAdmin(admin.ModelAdmin):
    list_display = ("profile", "directorate", "assigned_at")
    list_filter = ("directorate",)

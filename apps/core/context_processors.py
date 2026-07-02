from django.db import OperationalError, ProgrammingError

from .models import SystemSetting


def system_context(request):
    try:
        settings_map = {
            item.key: item.value for item in SystemSetting.objects.all()
        } if SystemSetting.objects.exists() else {}
    except (OperationalError, ProgrammingError):
        settings_map = {}
    return {
        "system_name": settings_map.get("system_name", "Plataforma de Vigilancia Socioassistencial"),
        "system_reference_year": settings_map.get("system_reference_year", "2026"),
        "logo_url": settings_map.get("logo_url", "https://xvyaaavcbxskmunmhwcg.supabase.co/storage/v1/object/public/system-assets/logo-1766148734971.png"),
    }

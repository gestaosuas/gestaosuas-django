from django.db import OperationalError, ProgrammingError

from .models import SystemSetting


def system_context(request):
    try:
        settings_map = {item.key: item.value for item in SystemSetting.objects.all()}
    except (OperationalError, ProgrammingError):
        settings_map = {}
    return {
        "system_name": settings_map.get("system_name", "Plataforma de Vigilancia Socioassistencial"),
        "system_reference_year": settings_map.get("system_reference_year", "2026"),
        "logo_url": settings_map.get("logo_url", "/static/img/logo-navbar.png"),
    }


def user_profile_context(request):
    user = getattr(request, "user", None)
    profile = None
    if user and user.is_authenticated:
        try:
            profile = getattr(user, "profile", None)
        except (OperationalError, ProgrammingError):
            pass
    return {"user_profile": profile}

from django.urls import path

from .views import (LandingView, MapManagementView, MapView,
                     SystemSettingsView, TvApiUrlsView, TvDashboardView)


app_name = "core"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("settings/", SystemSettingsView.as_view(), name="settings"),
    path("settings/mapas/", MapManagementView.as_view(), name="map_management"),
    path("mapas/", MapView.as_view(), name="map"),
    path("tv/", TvDashboardView.as_view(), name="tv-dashboard"),
    path("tv-api/urls/", TvApiUrlsView.as_view(), name="tv-api-urls"),
]

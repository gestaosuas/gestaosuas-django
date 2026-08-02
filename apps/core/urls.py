from django.urls import path

from .views import (LandingView, MapManagementView, MapView,
                     NarrativeReportDeleteView, NotificationsMarkReadView,
                     NotificationsUnreadView, ProtectedMediaView,
                     SystemSettingsView, TvApiUrlsView, TvDashboardView)


app_name = "core"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("settings/", SystemSettingsView.as_view(), name="settings"),
    path("settings/mapas/", MapManagementView.as_view(), name="map_management"),
    path("mapas/", MapView.as_view(), name="map"),
    path("tv/", TvDashboardView.as_view(), name="tv-dashboard"),
    path("tv-api/urls/", TvApiUrlsView.as_view(), name="tv-api-urls"),
    path("notifications/unread/", NotificationsUnreadView.as_view(), name="notifications-unread"),
    path("notifications/mark-read/", NotificationsMarkReadView.as_view(), name="notifications-mark-read"),
    path("media-protegido/<path:file_path>/", ProtectedMediaView.as_view(), name="protected-media"),
    path("relatorio-narrativo/excluir/", NarrativeReportDeleteView.as_view(), name="narrative-report-delete"),
]

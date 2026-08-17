from django.urls import path

from .views import (LandingView, ManifestView, MapManagementView, MapView,
                     NarrativeReportDeleteView, NotificationsListView,
                     NotificationsMarkReadView, NotificationsUnreadView,
                     ProtectedMediaView, ServiceWorkerView, SystemSettingsView,
                     TvApiUrlsView, TvDashboardView)


app_name = "core"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("manifest.json", ManifestView.as_view(), name="manifest"),
    path("sw.js", ServiceWorkerView.as_view(), name="service-worker"),
    path("settings/", SystemSettingsView.as_view(), name="settings"),
    path("settings/mapas/", MapManagementView.as_view(), name="map_management"),
    path("mapas/", MapView.as_view(), name="map"),
    path("tv/", TvDashboardView.as_view(), name="tv-dashboard"),
    path("tv-api/urls/", TvApiUrlsView.as_view(), name="tv-api-urls"),
    path("notifications/", NotificationsListView.as_view(), name="notifications-list"),
    path("notifications/unread/", NotificationsUnreadView.as_view(), name="notifications-unread"),
    path("notifications/mark-read/", NotificationsMarkReadView.as_view(), name="notifications-mark-read"),
    path("media-protegido/<path:file_path>/", ProtectedMediaView.as_view(), name="protected-media"),
    path("relatorio-narrativo/excluir/", NarrativeReportDeleteView.as_view(), name="narrative-report-delete"),
]

from django.urls import path
from .views import (
    CrasHomeView, CrasCreateUpdateView, CrasDataView,
    CrasMonthlyNarrativeView, CrasNarrativeListView,
    CrasQuickEditView
)

app_name = "cras"

urlpatterns = [
    path("<dir_slug:pk>/", CrasHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", CrasCreateUpdateView.as_view(), name="form"),
    path("<dir_slug:pk>/dados/", CrasDataView.as_view(), name="data"),
    path("<dir_slug:pk>/relatorio-mensal/", CrasMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("<dir_slug:pk>/relatorios/", CrasNarrativeListView.as_view(), name="reports"),
    path("quick-edit/", CrasQuickEditView.as_view(), name="quick-edit"),
]

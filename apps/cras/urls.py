from django.urls import path
from .views import (
    CrasHomeView, CrasCreateUpdateView, CrasDataView,
    CrasMonthlyNarrativeView, CrasNarrativeListView,
    CrasQuickEditView, CrasDeleteMonthView
)

app_name = "cras"

urlpatterns = [
    # quick-edit/ precisa vir ANTES de <dir_slug:pk>/, senão o converter
    # captura "quick-edit" como slug de diretoria (ver apps/creasidoso/urls.py).
    path("quick-edit/", CrasQuickEditView.as_view(), name="quick-edit"),
    path("<dir_slug:pk>/", CrasHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", CrasCreateUpdateView.as_view(), name="form"),
    path("<dir_slug:pk>/dados/", CrasDataView.as_view(), name="data"),
    path("<dir_slug:pk>/dados/excluir-mes/", CrasDeleteMonthView.as_view(), name="delete-month"),
    path("<dir_slug:pk>/relatorio-mensal/", CrasMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("<dir_slug:pk>/relatorios/", CrasNarrativeListView.as_view(), name="reports"),
]

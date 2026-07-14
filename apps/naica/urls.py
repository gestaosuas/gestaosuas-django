from django.urls import path
from .views import (
    NaicaHomeView, NaicaCreateUpdateView, NaicaDataView,
    NaicaMonthlyNarrativeView, NaicaNarrativeListView,
    NaicaQuickEditView, NaicaDeleteMonthView
)

app_name = "naica"

urlpatterns = [
    # quick-edit/ precisa vir ANTES de <dir_slug:pk>/, senão o converter
    # captura "quick-edit" como slug de diretoria (ver apps/creasidoso/urls.py).
    path("quick-edit/", NaicaQuickEditView.as_view(), name="quick-edit"),
    path("<dir_slug:pk>/", NaicaHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", NaicaCreateUpdateView.as_view(), name="form"),
    path("<dir_slug:pk>/dados/", NaicaDataView.as_view(), name="data"),
    path("<dir_slug:pk>/dados/excluir-mes/", NaicaDeleteMonthView.as_view(), name="delete-month"),
    path("<dir_slug:pk>/relatorio-mensal/", NaicaMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("<dir_slug:pk>/relatorios/", NaicaNarrativeListView.as_view(), name="reports"),
]

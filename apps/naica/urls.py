from django.urls import path
from .views import (
    NaicaHomeView, NaicaCreateUpdateView, NaicaDataView,
    NaicaMonthlyNarrativeView, NaicaNarrativeListView,
    NaicaQuickEditView
)

app_name = "naica"

urlpatterns = [
    path("<dir_slug:pk>/", NaicaHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", NaicaCreateUpdateView.as_view(), name="form"),
    path("<dir_slug:pk>/dados/", NaicaDataView.as_view(), name="data"),
    path("<dir_slug:pk>/relatorio-mensal/", NaicaMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("<dir_slug:pk>/relatorios/", NaicaNarrativeListView.as_view(), name="reports"),
    path("quick-edit/", NaicaQuickEditView.as_view(), name="quick-edit"),
]

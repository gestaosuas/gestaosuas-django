from django.urls import path
from .views import (
    CreasHomeView, CreasIdosoFormView, CreasPcdFormView,
    CreasIdosoDataView, CreasPcdDataView,
    CreasMonthlyNarrativeView, CreasNarrativeListView,
    CreasIdosoQuickEditView, CreasPcdQuickEditView
)

app_name = "creasidoso"

urlpatterns = [
    # As rotas de quick-edit precisam vir ANTES de <dir_slug:pk>/, senão o
    # converter captura "quick-edit-idoso"/"quick-edit-pcd" como slug de diretoria.
    path("quick-edit-idoso/", CreasIdosoQuickEditView.as_view(), name="quick-edit-idoso"),
    path("quick-edit-pcd/", CreasPcdQuickEditView.as_view(), name="quick-edit-pcd"),
    path("<dir_slug:pk>/", CreasHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher-idoso/", CreasIdosoFormView.as_view(), name="form-idoso"),
    path("<dir_slug:pk>/preencher-pcd/", CreasPcdFormView.as_view(), name="form-pcd"),
    path("<dir_slug:pk>/dados-idoso/", CreasIdosoDataView.as_view(), name="data-idoso"),
    path("<dir_slug:pk>/dados-pcd/", CreasPcdDataView.as_view(), name="data-pcd"),
    path("<dir_slug:pk>/relatorio-mensal/", CreasMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("<dir_slug:pk>/relatorios/", CreasNarrativeListView.as_view(), name="reports"),
]

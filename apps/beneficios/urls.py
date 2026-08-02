from django.urls import path
from .views import (
    BeneficiosHomeView, BeneficiosCreateUpdateView, BeneficiosDataView,
    BeneficiosMonthlyNarrativeView, BeneficiosNarrativeEditorView,
    BeneficiosQuickEditView, BeneficiosDeleteMonthView
)

app_name = "beneficios"

urlpatterns = [
    path("painel/", BeneficiosHomeView.as_view(), name="home"),
    path("atualizar/", BeneficiosCreateUpdateView.as_view(), name="update"),
    path("dados/", BeneficiosDataView.as_view(), name="data"),
    path("dados/excluir-mes/", BeneficiosDeleteMonthView.as_view(), name="delete-month"),
    path("relatorio-mensal/", BeneficiosMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("relatorio-mensal/editor/", BeneficiosNarrativeEditorView.as_view(), name="narrative-editor"),
    path("quick-edit/", BeneficiosQuickEditView.as_view(), name="quick-edit"),
]

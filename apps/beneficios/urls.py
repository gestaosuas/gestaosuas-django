from django.urls import path
from .views import (
    BeneficiosHomeView, BeneficiosCreateUpdateView, BeneficiosDataView,
    BeneficiosMonthlyNarrativeView, BeneficiosNarrativeListView,
    BeneficiosQuickEditView
)

app_name = "beneficios"

urlpatterns = [
    path("painel/", BeneficiosHomeView.as_view(), name="home"),
    path("atualizar/", BeneficiosCreateUpdateView.as_view(), name="update"),
    path("dados/", BeneficiosDataView.as_view(), name="data"),
    path("relatorio-mensal/", BeneficiosMonthlyNarrativeView.as_view(), name="monthly-report"),
    path("relatorios/", BeneficiosNarrativeListView.as_view(), name="reports"),
    path("quick-edit/", BeneficiosQuickEditView.as_view(), name="quick-edit"),
]

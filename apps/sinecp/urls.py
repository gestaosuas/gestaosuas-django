from django.urls import path
from .views import (
    SineCpHomeView, SineCreateUpdateView, QualificacaoCreateUpdateView,
    SineDataView, QualificacaoDataView, SineMonthlyNarrativeView,
    QualificacaoMonthlyNarrativeView, SineNarrativeListView,
    QualificacaoNarrativeListView, SineQuickEditView, QualificacaoQuickEditView,
    SineDeleteMonthView, QualificacaoDeleteMonthView
)

app_name = "sinecp"

urlpatterns = [
    path("painel/", SineCpHomeView.as_view(), name="home"),
    
    # SINE
    path("sine/preencher/", SineCreateUpdateView.as_view(), name="sine-form"),
    path("sine/dados/", SineDataView.as_view(), name="sine-data"),
    path("sine/dados/excluir-mes/", SineDeleteMonthView.as_view(), name="sine-delete-month"),
    path("sine/relatorio-mensal/", SineMonthlyNarrativeView.as_view(), name="sine-monthly-report"),
    path("sine/relatorios/", SineNarrativeListView.as_view(), name="sine-reports"),
    path("sine/quick-edit/", SineQuickEditView.as_view(), name="sine-quick-edit"),

    # Qualificação
    path("qualificacao/preencher/", QualificacaoCreateUpdateView.as_view(), name="qualificacao-form"),
    path("qualificacao/dados/", QualificacaoDataView.as_view(), name="qualificacao-data"),
    path("qualificacao/dados/excluir-mes/", QualificacaoDeleteMonthView.as_view(), name="qualificacao-delete-month"),
    path("qualificacao/relatorio-mensal/", QualificacaoMonthlyNarrativeView.as_view(), name="qualificacao-monthly-report"),
    path("qualificacao/relatorios/", QualificacaoNarrativeListView.as_view(), name="qualificacao-reports"),
    path("qualificacao/quick-edit/", QualificacaoQuickEditView.as_view(), name="qualificacao-quick-edit"),
]

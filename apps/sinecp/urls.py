from django.urls import path
from .views import (
    SineCpHomeView, SineCreateUpdateView, QualificacaoCreateUpdateView,
    SineDataView, QualificacaoDataView, SineMonthlyNarrativeView,
    QualificacaoMonthlyNarrativeView, SineNarrativeEditorView,
    QualificacaoNarrativeEditorView, SineQuickEditView, QualificacaoQuickEditView,
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
    path("sine/relatorio-mensal/editor/", SineNarrativeEditorView.as_view(), name="sine-narrative-editor"),
    path("sine/quick-edit/", SineQuickEditView.as_view(), name="sine-quick-edit"),

    # Qualificação
    path("qualificacao/preencher/", QualificacaoCreateUpdateView.as_view(), name="qualificacao-form"),
    path("qualificacao/dados/", QualificacaoDataView.as_view(), name="qualificacao-data"),
    path("qualificacao/dados/excluir-mes/", QualificacaoDeleteMonthView.as_view(), name="qualificacao-delete-month"),
    path("qualificacao/relatorio-mensal/", QualificacaoMonthlyNarrativeView.as_view(), name="qualificacao-monthly-report"),
    path("qualificacao/relatorio-mensal/editor/", QualificacaoNarrativeEditorView.as_view(), name="qualificacao-narrative-editor"),
    path("qualificacao/quick-edit/", QualificacaoQuickEditView.as_view(), name="qualificacao-quick-edit"),
]

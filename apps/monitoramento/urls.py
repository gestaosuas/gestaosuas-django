from django.urls import path
from .views import (
    MonitoramentoHomeView, MonitoramentoFormView,
    MonitoramentoDataView, MonitoramentoDeleteMonthView,
)

app_name = "monitoramento"

urlpatterns = [
    path("<dir_slug:pk>/", MonitoramentoHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", MonitoramentoFormView.as_view(), name="form"),
    path("<dir_slug:pk>/dados/", MonitoramentoDataView.as_view(), name="data"),
    path("<dir_slug:pk>/dados/excluir-mes/", MonitoramentoDeleteMonthView.as_view(), name="delete-month"),
]

from django.urls import path
from .views import MonitoramentoHomeView, MonitoramentoFormView

app_name = "monitoramento"

urlpatterns = [
    path("<dir_slug:pk>/", MonitoramentoHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", MonitoramentoFormView.as_view(), name="form"),
]

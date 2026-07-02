from django.urls import path
from . import views

app_name = "casamulher"

urlpatterns = [
    # Dashboard
    path("<dir_slug:pk>/", views.CasaMulherHomeView.as_view(), name="home"),

    # Forms
    path("<dir_slug:pk>/atualizar/casa-da-mulher/", views.CasaDaMulherFormView.as_view(), name="form-casa-da-mulher"),
    path("<dir_slug:pk>/atualizar/diversidade/", views.DiversidadeFormView.as_view(), name="form-diversidade"),
    path("<dir_slug:pk>/atualizar/nucleo-diversidade/", views.NucleoDiversidadeFormView.as_view(), name="form-nucleo-diversidade"),

    # Spreadsheets
    path("<dir_slug:pk>/dados/casa-da-mulher/", views.CasaDaMulherDataView.as_view(), name="data-casa-da-mulher"),
    path("<dir_slug:pk>/dados/diversidade/", views.DiversidadeDataView.as_view(), name="data-diversidade"),
    path("<dir_slug:pk>/dados/nucleo-diversidade/", views.NucleoDiversidadeDataView.as_view(), name="data-nucleo-diversidade"),
    
    # Quick Edit AJAX APIs
    path("quick-edit/casa-da-mulher/", views.CasaDaMulherQuickEditView.as_view(), name="quick-edit-casa-da-mulher"),
    path("quick-edit/diversidade/", views.DiversidadeQuickEditView.as_view(), name="quick-edit-diversidade"),
    path("quick-edit/nucleo-diversidade/", views.NucleoDiversidadeQuickEditView.as_view(), name="quick-edit-nucleo-diversidade"),
]

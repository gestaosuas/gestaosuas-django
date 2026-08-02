from django.urls import path
from . import views

app_name = "protecaoespecial"

urlpatterns = [
    path("<dir_slug:pk>/", views.ProtecaoEspecialHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/atualizar/protetivo/", views.CreasProtetivoFormView.as_view(), name="form-protetivo"),
    path("<dir_slug:pk>/atualizar/socioeducativo/", views.CreasSocioeducativoFormView.as_view(), name="form-socioeducativo"),
    path("<dir_slug:pk>/dados/protetivo/", views.CreasProtetivoDataView.as_view(), name="data-protetivo"),
    path("<dir_slug:pk>/dados/protetivo/excluir-mes/", views.CreasProtetivoDeleteMonthView.as_view(), name="delete-month-protetivo"),
    path("<dir_slug:pk>/dados/socioeducativo/", views.CreasSocioeducativoDataView.as_view(), name="data-socioeducativo"),
    path("<dir_slug:pk>/dados/socioeducativo/excluir-mes/", views.CreasSocioeducativoDeleteMonthView.as_view(), name="delete-month-socioeducativo"),
    path("<dir_slug:pk>/relatorio-mensal/protetivo/", views.CreasProtetivoMonthlyNarrativeView.as_view(), name="protetivo-monthly-report"),
    path("<dir_slug:pk>/relatorio-mensal/protetivo/editor/", views.CreasProtetivoNarrativeEditorView.as_view(), name="protetivo-narrative-editor"),
    path("<dir_slug:pk>/relatorio-mensal/socioeducativo/", views.CreasSocioeducativoMonthlyNarrativeView.as_view(), name="socioeducativo-monthly-report"),
    path("<dir_slug:pk>/relatorio-mensal/socioeducativo/editor/", views.CreasSocioeducativoNarrativeEditorView.as_view(), name="socioeducativo-narrative-editor"),
    path("quick-edit/protetivo/", views.CreasProtetivoQuickEditView.as_view(), name="quick-edit-protetivo"),
    path("quick-edit/socioeducativo/", views.CreasSocioeducativoQuickEditView.as_view(), name="quick-edit-socioeducativo"),
]

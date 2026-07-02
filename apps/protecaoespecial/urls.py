from django.urls import path
from . import views

app_name = "protecaoespecial"

urlpatterns = [
    path("<dir_slug:pk>/", views.ProtecaoEspecialHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/atualizar/protetivo/", views.CreasProtetivoFormView.as_view(), name="form-protetivo"),
    path("<dir_slug:pk>/atualizar/socioeducativo/", views.CreasSocioeducativoFormView.as_view(), name="form-socioeducativo"),
    path("<dir_slug:pk>/dados/protetivo/", views.CreasProtetivoDataView.as_view(), name="data-protetivo"),
    path("<dir_slug:pk>/dados/socioeducativo/", views.CreasSocioeducativoDataView.as_view(), name="data-socioeducativo"),
    path("quick-edit/protetivo/", views.CreasProtetivoQuickEditView.as_view(), name="quick-edit-protetivo"),
    path("quick-edit/socioeducativo/", views.CreasSocioeducativoQuickEditView.as_view(), name="quick-edit-socioeducativo"),
]

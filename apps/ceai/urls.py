from django.urls import path
from . import views

app_name = "ceai"

urlpatterns = [
    path("", views.CeaiDashboardView.as_view(), name="dashboard"),
    path("unidade/<str:unit>/atualizar/", views.CeaiUpdateDataView.as_view(), name="update_data"),
    path("unidade/<str:unit>/oficinas/", views.CeaiOficinasView.as_view(), name="oficinas"),
    path("unidade/<str:unit>/categorias/", views.CeaiCategoriesView.as_view(), name="categories"),
    path("<dir_slug:pk>/relatorio-mensal/", views.CeaiMonthlyNarrativeView.as_view(), name="ceai_monthly_report"),
    path("relatorios/", views.CeaiReportsListView.as_view(), name="reports"),
    path("dados/", views.CeaiDataListView.as_view(), name="data_list"),
    path("quick-edit/", views.CeaiQuickEditView.as_view(), name="quick_edit"),
    path("api/categorias/", views.CeaiCategoryApiView.as_view(), name="api_categories"),
    path("api/oficinas/", views.CeaiOficinaApiView.as_view(), name="api_oficinas"),
]

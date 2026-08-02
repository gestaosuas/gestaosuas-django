from django.urls import path
from . import views

app_name = 'poprua'

urlpatterns = [
    path('', views.PopRuaDashboardView.as_view(), name='dashboard'),
    path('dados/', views.PopRuaDataListView.as_view(), name='data_list'),
    path('dados/excluir-mes/', views.PopRuaDeleteMonthView.as_view(), name='delete_month'),
    path('atualizar/', views.PopRuaUpdateView.as_view(), name='update_data'),
    path('atualizar/<uuid:pk>/', views.PopRuaUpdateView.as_view(), name='update_data_edit'),
    path('quick-edit/', views.PopRuaQuickEditView.as_view(), name='quick_edit'),
    path('relatorio-mensal/', views.PopRuaMonthlyNarrativeView.as_view(), name='monthly-report'),
    path('relatorio-mensal/editor/', views.PopRuaNarrativeEditorView.as_view(), name='narrative-editor'),
]

from django.urls import path
from . import views

app_name = 'poprua'

urlpatterns = [
    path('', views.PopRuaDashboardView.as_view(), name='dashboard'),
    path('dados/', views.PopRuaDataListView.as_view(), name='data_list'),
    path('atualizar/', views.PopRuaUpdateView.as_view(), name='update_data'),
    path('atualizar/<uuid:pk>/', views.PopRuaUpdateView.as_view(), name='update_data_edit'),
    path('quick-edit/', views.PopRuaQuickEditView.as_view(), name='quick_edit'),
]

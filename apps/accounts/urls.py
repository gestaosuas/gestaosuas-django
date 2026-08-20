from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from .forms import EmailAuthenticationForm
from .views import (
    UserCreateView,
    UserDeactivateView,
    UserListView,
    UserPermissionsView,
    UserReactivateView,
)


app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("usuarios/", UserListView.as_view(), name="user_list"),
    path("usuarios/novo/", UserCreateView.as_view(), name="user_create"),
    path("usuarios/<uuid:pk>/permissoes/", UserPermissionsView.as_view(), name="user_permissions"),
    path("usuarios/<uuid:pk>/excluir/", UserDeactivateView.as_view(), name="user_deactivate"),
    path("usuarios/<uuid:pk>/reativar/", UserReactivateView.as_view(), name="user_reactivate"),
]

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from .forms import EmailAuthenticationForm
from .views import UserListView, UserPermissionsView


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
    path("usuarios/<uuid:pk>/permissoes/", UserPermissionsView.as_view(), name="user_permissions"),
]

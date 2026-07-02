from django import forms
from django.contrib.auth.forms import AuthenticationForm


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="E-mail ou usuario",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Digite seu e-mail"}),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Digite sua senha"}),
    )

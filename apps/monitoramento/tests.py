import uuid

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, ProfileDirectorate, User
from apps.directorates.models import Directorate


def make_directorate(name=None):
    """Diretoria nova e isolada (tabela managed=False, id sem default automatico)."""
    return Directorate.objects.create(
        id=uuid.uuid4(),
        name=name or f"Diretoria Teste {uuid.uuid4().hex[:8]}",
    )


def make_user(email=None, password="senha12345", role=Profile.ROLE_USER, full_name="Usuario Teste", **profile_kwargs):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(username=email, email=email, password=password)
    profile = Profile.objects.create(user=user, full_name=full_name, role=role, **profile_kwargs)
    return user, profile


class MonitoramentoBaseMixinAccessTests(TestCase):
    """
    Cobre a mudanca de MonitoramentoBaseMixin de LoginRequiredMixin para
    DirectorateAccessMixin: antes, qualquer usuario autenticado podia acessar o
    dashboard de monitoramento de QUALQUER diretoria; agora o acesso e restrito
    a admins/superusers ou usuarios com vinculo (primary_directorate ou
    ProfileDirectorate) com aquela diretoria especifica.
    """

    def setUp(self):
        self.password = "senha12345"
        self.directorate = make_directorate()
        self.url = reverse("monitoramento:home", kwargs={"pk": self.directorate.pk})

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_user_can_access_any_directorate(self):
        email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        make_user(email=email, password=self.password, role=Profile.ROLE_ADMIN)
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_any_directorate(self):
        email = f"super-{uuid.uuid4().hex[:8]}@example.com"
        superuser = User.objects.create_superuser(username=email, email=email, password=self.password)
        Profile.objects.create(user=superuser, full_name="Super User", role=Profile.ROLE_USER)
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_without_directorate_link_is_redirected(self):
        email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        make_user(email=email, password=self.password, role=Profile.ROLE_USER)
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:landing"))

    def test_user_with_primary_directorate_match_can_access(self):
        email = f"primary-{uuid.uuid4().hex[:8]}@example.com"
        user, profile = make_user(
            email=email, password=self.password, role=Profile.ROLE_USER,
            primary_directorate=self.directorate,
        )
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_user_with_profile_directorate_link_can_access(self):
        email = f"linked-{uuid.uuid4().hex[:8]}@example.com"
        user, profile = make_user(email=email, password=self.password, role=Profile.ROLE_USER)
        ProfileDirectorate.objects.create(profile=profile, directorate=self.directorate)
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_user_linked_to_a_different_directorate_is_still_redirected(self):
        other_directorate = make_directorate()
        email = f"other-{uuid.uuid4().hex[:8]}@example.com"
        user, profile = make_user(
            email=email, password=self.password, role=Profile.ROLE_USER,
            primary_directorate=other_directorate,
        )
        self.client.login(username=email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:landing"))


class MonitoramentoHomeRedirectTests(TestCase):
    """MonitoramentoHomeView.get() (2026-07-25): diretor/agente nao veem mais
    o dashboard de abas de Subvencao/Emendas e Fundos/Outros - vao direto pra
    lista de Instrumental de Visitas. Admin continua vendo o dashboard normal.
    Diretoria generica (sem "subvencao"/"emenda"/"fundo"/"outros" no nome) nao
    e afetada."""

    def setUp(self):
        self.password = "senha12345"

    def test_diretor_redirected_for_subvencao(self):
        # Sufixo unico pra nao colidir com o slug de uma Directorate real
        # "Subvenção" ja existente no banco (testes rodam contra o banco de
        # dev real - ver CLAUDE.md secao Testes).
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role=Profile.ROLE_DIRECTOR, primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertRedirects(
            response, reverse("directorates:visit-list", kwargs={"pk": directorate.pk}),
            fetch_redirect_response=False,
        )

    def test_agente_redirected_for_emendas_e_fundos(self):
        directorate = make_directorate(name=f"Emendas e Fundos Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role="agente", primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertRedirects(
            response, reverse("directorates:visit-list", kwargs={"pk": directorate.pk}),
            fetch_redirect_response=False,
        )

    def test_agente_redirected_for_outros(self):
        directorate = make_directorate(name=f"Outros Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role="agente", primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertRedirects(
            response, reverse("directorates:visit-list", kwargs={"pk": directorate.pk}),
            fetch_redirect_response=False,
        )

    def test_admin_not_redirected_for_subvencao(self):
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(password=self.password, role=Profile.ROLE_ADMIN)
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertEqual(response.status_code, 200)

    def test_diretor_not_redirected_for_generic_directorate(self):
        directorate = make_directorate()
        user, profile = make_user(
            password=self.password, role=Profile.ROLE_DIRECTOR, primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertEqual(response.status_code, 200)

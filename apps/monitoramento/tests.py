import uuid
from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, ProfileDirectorate, User
from apps.directorates.models import Directorate, FormDelegation, Osc, Visit


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


def make_osc(directorate, name=None):
    return Osc.objects.create(id=uuid.uuid4(), name=name or f"OSC Teste {uuid.uuid4().hex[:8]}", directorate=directorate)


def make_visit(directorate, osc=None, user=None):
    return Visit.objects.create(
        id=uuid.uuid4(),
        osc=osc or make_osc(directorate),
        directorate=directorate,
        visit_date=date.today(),
        visit_time=time(9, 0),
        user_id=user.pk if user else None,
    )


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


class MonitoramentoHomeTabRestrictionTests(TestCase):
    """MonitoramentoHomeView.get_context_data() (2026-07-25, corrigido no
    mesmo dia): diretor/agente continuam no MESMO dashboard de abas de
    Subvencao/Emendas e Fundos/Outros (nao sao mais redirecionados pra fora,
    pra `directorates:visit-list` - o usuario pediu pra desfazer isso) - so a
    aba (`dashboard_tab`) e restrita via allowlist: so `visits`/`reports` (so
    `visits` em Outros). Admin continua vendo qualquer aba, com default
    `overview`. Diretoria generica nao e afetada (nao usa esse sistema de
    abas)."""

    def setUp(self):
        self.password = "senha12345"

    def test_diretor_lands_on_visits_tab_for_subvencao_by_default(self):
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role=Profile.ROLE_DIRECTOR, primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "visits")
        self.assertFalse(response.context["is_admin_user"])

    def test_agente_cannot_reach_oscs_tab_via_querystring(self):
        directorate = make_directorate(name=f"Emendas e Fundos Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role="agente", primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=oscs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "visits")

    def test_agente_can_reach_reports_tab_for_emendas_e_fundos(self):
        directorate = make_directorate(name=f"Emendas e Fundos Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role="agente", primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=reports")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "reports")

    def test_agente_cannot_reach_reports_tab_for_outros(self):
        directorate = make_directorate(name=f"Outros Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(
            password=self.password, role="agente", primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=reports")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "visits")

    def test_admin_defaults_to_overview_for_subvencao(self):
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(password=self.password, role=Profile.ROLE_ADMIN)
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "overview")
        self.assertTrue(response.context["is_admin_user"])

    def test_admin_can_reach_oscs_tab(self):
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        user, profile = make_user(password=self.password, role=Profile.ROLE_ADMIN)
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=oscs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_tab"], "oscs")

    def test_diretor_not_redirected_for_generic_directorate(self):
        directorate = make_directorate()
        user, profile = make_user(
            password=self.password, role=Profile.ROLE_DIRECTOR, primary_directorate=directorate,
        )
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}))
        self.assertEqual(response.status_code, 200)


class MonitoramentoAgentePeerVisibilityTests(TestCase):
    """2026-08-19, pedido explicito do usuario: "somente em monitoramento, no
    caso em emendas e fundos e subvencao, as visitas criadas por um agente da
    mesma diretoria, pode ser visto e editado por outros agentes da mesma
    diretoria (semelhante ao que o Diretor ve)". Cobre a mudanca em
    MonitoramentoHomeView.get_context_data() (dashboard_visits) e no acesso
    direto por URL (VisitAccessMixin, via directorates:visit-instrumental).
    "Outros" fica de fora (so Subvencao/Emendas e Fundos) - is_subvencao_directorate
    ja exclui "Outros" pelo nome."""

    def setUp(self):
        self.password = "senha12345"

    def test_agente_sees_coworkers_visit_in_subvencao_dashboard(self):
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        owner, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        visit = make_visit(directorate, user=owner)
        viewer, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=viewer.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits")
        self.assertEqual(response.status_code, 200)
        self.assertIn(visit, response.context["dashboard_visits"])

    def test_agente_sees_coworkers_visit_in_emendas_dashboard(self):
        directorate = make_directorate(name=f"Emendas e Fundos Teste {uuid.uuid4().hex[:8]}")
        owner, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        visit = make_visit(directorate, user=owner)
        viewer, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=viewer.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits")
        self.assertEqual(response.status_code, 200)
        self.assertIn(visit, response.context["dashboard_visits"])

    def test_agente_still_cannot_see_coworkers_visit_in_outros(self):
        """"Outros" nao entra na nova regra - continua so dono/delegado."""
        directorate = make_directorate(name=f"Outros Teste {uuid.uuid4().hex[:8]}")
        owner, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        visit = make_visit(directorate, user=owner)
        viewer, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=viewer.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(visit, response.context["dashboard_visits"])

    def test_agente_does_not_see_admin_created_visit_in_subvencao(self):
        """Mesma exclusao ja aplicada pro diretor: visita de admin nao conta
        como "de um agente", mesmo dentro de Subvencao/Emendas e Fundos."""
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        admin, _ = make_user(password=self.password, role=Profile.ROLE_ADMIN)
        visit = make_visit(directorate, user=admin)
        viewer, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=viewer.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(visit, response.context["dashboard_visits"])

    def test_agente_sees_admin_created_visit_in_subvencao_when_delegated(self):
        """Regressao real 2026-08-20: a exclusao do teste acima tinha virado
        absoluta - nem uma FormDelegation explicita conseguia furar ela,
        quebrando o caso de uso mais comum de delegacao (admin cria a visita
        e delega pra um agente preencher). Reportado pelo usuario em producao
        ("tentamos delegar a um agente, mas parece que nao funcionou")."""
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        admin, _ = make_user(password=self.password, role=Profile.ROLE_ADMIN)
        visit = make_visit(directorate, user=admin)
        agente, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        FormDelegation.objects.create(
            id=uuid.uuid4(), visit=visit, user_id=agente.pk, delegated_by=admin.pk,
        )
        self.client.login(username=agente.username, password=self.password)
        response = self.client.get(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits")
        self.assertEqual(response.status_code, 200)
        self.assertIn(visit, response.context["dashboard_visits"])

    def test_agente_can_edit_coworkers_visit_in_subvencao(self):
        """Diferente do diretor (so leitura em visita alheia), agente ganha
        edicao completa na visita de um colega da mesma diretoria."""
        directorate = make_directorate(name=f"Subvenção Teste {uuid.uuid4().hex[:8]}")
        owner, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        visit = make_visit(directorate, user=owner)
        coworker, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=coworker.username, password=self.password)
        get_response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}),
            {"status": "draft", "observacoes": "colega editando", "recomendacoes": ""},
        )
        self.assertEqual(post_response.status_code, 302)

    def test_agente_cannot_edit_coworkers_visit_in_outros(self):
        directorate = make_directorate(name=f"Outros Teste {uuid.uuid4().hex[:8]}")
        owner, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        visit = make_visit(directorate, user=owner)
        coworker, _ = make_user(password=self.password, role="agente", primary_directorate=directorate)
        self.client.login(username=coworker.username, password=self.password)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 403)

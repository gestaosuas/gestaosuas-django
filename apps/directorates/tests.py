"""
Testes do app `directorates`.

Foco principal: o `DirectorateAccessMixin` (apps/accounts/mixins.py) foi ligado a
praticamente todas as views deste app nesta sessão (antes elas só tinham
`LoginRequiredMixin`). Isso introduziu controle de acesso por diretoria via dois
novos mixins locais:

- `DirectorateScopedMixin` — para views cujo `<dir_slug:pk>` na URL é a própria
  diretoria (ex: OscListView, VisitListView, WorkPlanCreateView...).
- `OscScopedMixin` / `VisitScopedMixin` / `WorkPlanScopedMixin` — para views cujo
  `<uuid:pk>` identifica um objeto (Osc/Visit/WorkPlan); o acesso é resolvido a
  partir da diretoria a que esse objeto pertence.

Também cobrimos o fluxo básico de CRUD de OSC/Visita/Plano de trabalho e o
`dir_slug` converter, e uma correção de bug real encontrada no diff
(`WorkPlanCreateView.form_valid` passou a setar `user_id`, campo NOT NULL no
banco que antes ficava sem valor).

Banco: TestCase roda em transação com rollback automático contra o banco de
dev real (settings.DATABASES["default"]["TEST"]["NAME"] aponta pro mesmo banco).
Nenhuma `Directorate` existente é criada/alterada/apagada — só lida via
`Directorate.objects.annotate(...).first()`. Osc/Visit/WorkPlan/FormDelegation
usados nos testes são sempre criados do zero dentro do teste.
"""
import uuid
from datetime import date, time

from django.db.models import Count
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Profile, ProfileDirectorate, User
from apps.directorates.models import Directorate, FormDelegation, Osc, Visit, WorkPlan
from apps.directorates.views import is_subvencao_directorate

# WhiteNoise's CompressedManifestStaticFilesStorage (config/settings.py STORAGES)
# exige que `collectstatic` já tenha rodado (manifesto staticfiles.json). Como os
# testes rodam direto no host sem collectstatic, qualquer template que renderize
# de verdade (não apenas redirects) e referencie `{% static %}` quebraria com
# "Missing staticfiles manifest entry". Isso é puramente do ambiente de teste —
# trocamos para o storage simples só durante os testes deste módulo.
STATIC_TEST_STORAGES = {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}


def _unique_username(prefix="testuser"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_user(role="user", primary_directorate=None, linked_directorate=None, is_superuser=False):
    """Cria um User + Profile de teste. Nunca reaproveita usuários reais do banco."""
    user = User.objects.create_user(
        username=_unique_username(),
        email=f"{_unique_username()}@example.com",
        password="testpass123",
        is_superuser=is_superuser,
    )
    Profile.objects.create(
        user=user,
        full_name="Usuario de Teste",
        role=role,
        primary_directorate=primary_directorate,
    )
    if linked_directorate is not None:
        ProfileDirectorate.objects.create(profile=user.profile, directorate=linked_directorate)
    return user


@override_settings(STORAGES=STATIC_TEST_STORAGES)
class DirectoratesTestBase(TestCase):
    """Diretoria compartilhada: a que tem mais OSCs cadastradas (dado real, nunca
    modificado — só lido)."""

    @classmethod
    def setUpTestData(cls):
        cls.directorate = (
            Directorate.objects.annotate(n_oscs=Count("oscs")).order_by("-n_oscs", "name").first()
        )
        cls.other_directorate = (
            Directorate.objects.exclude(pk=cls.directorate.pk)
            .annotate(n_oscs=Count("oscs"))
            .order_by("-n_oscs", "name")
            .first()
        )
        # `cls.directorate`/`cls.other_directorate` (as 2 com mais OSCs neste
        # banco de dev real) sao ambas Subvencao/Emendas e Fundos - qualquer
        # teste que precise de uma diretoria FORA do grupo com a regra de
        # colegas-se-veem (2026-08-19) deve usar esta em vez de assumir que
        # `cls.directorate` serve.
        cls.non_subvencao_directorate = next(
            (d for d in Directorate.objects.order_by("name") if not is_subvencao_directorate(d)),
            None,
        )

    def make_osc(self, name="OSC de Teste", directorate=None):
        return Osc.objects.create(
            id=uuid.uuid4(),
            name=name,
            directorate=directorate or self.directorate,
        )

    def make_visit(self, osc=None, directorate=None, user=None):
        return Visit.objects.create(
            id=uuid.uuid4(),
            osc=osc or self.make_osc(),
            directorate=directorate or self.directorate,
            visit_date=date.today(),
            visit_time=time(9, 0),
            user_id=user.pk if user else None,
        )

    def make_work_plan(self, osc=None, directorate=None, user=None):
        owner = user or make_user()
        return WorkPlan.objects.create(
            osc=osc or self.make_osc(),
            directorate=directorate or self.directorate,
            title="Plano de Teste",
            user_id=owner.pk,
        )


class DirectorateSlugConverterTests(DirectoratesTestBase):
    """Testa o `dir_slug` converter (apps/core/converters.py) via as URLs reais do app."""

    def test_reverse_with_uuid_pk_produces_friendly_slug_url(self):
        url = reverse("directorates:osc-list", kwargs={"pk": self.directorate.pk})
        self.assertIn(self.directorate.slug, url)
        self.assertNotIn(str(self.directorate.pk), url)

    def test_request_with_friendly_slug_path_resolves_to_directorate(self):
        """to_python() deve casar o slug amigável com a Directorate certa
        percorrendo e normalizando os nomes (NFD + lowercase + hifens)."""
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = f"/directorias/{self.directorate.slug}/oscs/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.directorate.pk)

    def test_request_with_raw_uuid_path_still_works(self):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = f"/directorias/{self.directorate.pk}/oscs/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_reverse_with_non_uuid_string_pk_does_not_crash(self):
        """Regressão do bug corrigido em 2026-07: DirectorateSlugConverter.to_url()
        só capturava (ValueError, TypeError) ao tentar `Directorate.objects.filter(pk=value)`
        com uma string não-UUID, mas o Django atual levanta ValidationError
        nesse caso — reverse() quebrava sem tratamento sempre que algum código
        passasse uma string arbitrária (não UUID, não instância de Directorate)
        como kwarg pk. Corrigido adicionando ValidationError ao except."""
        url = reverse("directorates:osc-list", kwargs={"pk": "string-que-nao-e-uuid"})
        self.assertEqual(url, "/directorias/string-que-nao-e-uuid/oscs/")

    def test_unknown_slug_redirects_regular_user_to_landing_instead_of_404(self):
        """Slug que não bate com nenhuma Directorate: to_python() retorna a
        string crua (comentário do próprio converter: 'Fallback to string if
        not found, though views might fail later'). Isso NÃO vira um 404
        limpo: DirectorateScopedMixin.get_directorate() faz
        `Directorate.objects.filter(pk=<string-invalida>)`, que levanta
        ValidationError (pk é UUIDField) — capturado pelo `except Exception`
        genérico de DirectorateAccessMixin.dispatch() e tratado como se fosse
        "diretoria não encontrada", redirecionando para core:landing.
        (Para admin/superuser, que pulam esse except, um slug totalmente
        desconhecido ainda pode virar 500 — ver debito técnico #10 no
        CLAUDE.md sobre ValidationError não capturada em get_directorate()
        para pk malformado; o caso de UUID válido mas inexistente já foi
        corrigido, ver DirectorateAccessMixinTests.test_nonexistent_directorate_gives_clean_404_for_admin.)"""
        user = make_user(role="user")
        self.client.force_login(user)
        response = self.client.get(
            "/directorias/esta-diretoria-nao-existe/oscs/", follow=False
        )
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)


class DirectorateAccessMixinTests(DirectoratesTestBase):
    """Cobre o comportamento novo introduzido pelo diff: DirectorateAccessMixin
    aplicado via DirectorateScopedMixin em views antes protegidas só por
    LoginRequiredMixin."""

    def _osc_list_url(self, directorate=None):
        return reverse("directorates:osc-list", kwargs={"pk": (directorate or self.directorate).pk})

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self._osc_list_url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_user_with_no_directorate_link_is_denied(self):
        user = make_user(role="user")
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url(), follow=False)
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)

    def test_user_with_primary_directorate_is_allowed(self):
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url())
        self.assertEqual(response.status_code, 200)

    def test_user_with_secondary_linked_directorate_is_allowed(self):
        user = make_user(role="agente", linked_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url())
        self.assertEqual(response.status_code, 200)

    def test_diretor_linked_only_to_a_different_directorate_is_denied(self):
        user = make_user(role="diretor", primary_directorate=self.other_directorate)
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url(), follow=False)
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)

    def test_admin_role_bypasses_directorate_link_requirement(self):
        user = make_user(role="admin")  # sem primary_directorate nem link algum
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url())
        self.assertEqual(response.status_code, 200)

    def test_superuser_bypasses_directorate_link_requirement(self):
        user = make_user(role="user", is_superuser=True)
        self.client.force_login(user)
        response = self.client.get(self._osc_list_url())
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_directorate_redirects_regular_user_to_landing(self):
        user = make_user(role="user")
        self.client.force_login(user)
        fake_pk = uuid.uuid4()
        response = self.client.get(
            reverse("directorates:osc-list", kwargs={"pk": fake_pk}), follow=False
        )
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)

    def test_nonexistent_directorate_gives_clean_404_for_admin(self):
        """Regressão do bug corrigido em 2026-07: DirectorateAccessMixin.dispatch()
        só chamava get_directorate() (que faz o 404 amigável) para usuários
        não-admin — admin/superuser pulavam direto pro super().dispatch(). Só
        que OscListView.get_context_data() fazia um SEGUNDO lookup redundante
        com `Directorate.objects.get(pk=self.kwargs["pk"])` (sem
        get_object_or_404), sem proteção nenhuma. Resultado: um admin acessando
        uma diretoria inexistente recebia uma Directorate.DoesNotExist não
        tratada (500). Corrigido trocando esse lookup redundante por
        `self.get_directorate()` (mesmo método já usado por dispatch(), que
        levanta Http404 de forma limpa) em OscListView/VisitListView/
        WorkPlanListView/MonitoringReportListView/WorkPlanCreateView/
        OscCreateView — as 6 ocorrências desse padrão no app."""
        admin = make_user(role="admin")
        self.client.force_login(admin)
        fake_pk = uuid.uuid4()
        response = self.client.get(reverse("directorates:osc-list", kwargs={"pk": fake_pk}))
        self.assertEqual(response.status_code, 404)


class ObjectScopedAccessMixinTests(DirectoratesTestBase):
    """Cobre OscScopedMixin/VisitScopedMixin/WorkPlanScopedMixin: views cujo
    <uuid:pk> identifica o objeto, não a diretoria — o acesso deve ser resolvido
    a partir de `objeto.directorate`."""

    def test_osc_update_forbidden_for_non_admin_with_directorate_access(self):
        """OSC vira admin-only pra criar/editar/excluir (2026-07-29, decisão
        explícita do usuário) — diretor/agente perdem acesso mesmo tendo
        vínculo com a diretoria da OSC. O dispatch() de admin em
        OscUpdateView roda antes de OscScopedMixin, então nem chega a
        resolver a diretoria do objeto."""
        osc = self.make_osc()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.get(reverse("directorates:osc-update", kwargs={"pk": osc.pk}))
        self.assertEqual(response.status_code, 403)

    def test_osc_update_denied_for_user_without_directorate_access(self):
        osc = self.make_osc()
        user = make_user(role="agente", primary_directorate=self.other_directorate)
        self.client.force_login(user)
        response = self.client.get(
            reverse("directorates:osc-update", kwargs={"pk": osc.pk}), follow=False
        )
        self.assertEqual(response.status_code, 403)

    def test_osc_update_nonexistent_object_is_forbidden_before_lookup_for_regular_user(self):
        """O guard de admin em OscUpdateView.dispatch() roda antes de
        OscScopedMixin resolver o objeto — um não-admin recebe 403 mesmo
        para um pk inexistente, sem nunca chegar no get_object_or_404."""
        user = make_user(role="user")
        self.client.force_login(user)
        response = self.client.get(
            reverse("directorates:osc-update", kwargs={"pk": uuid.uuid4()}), follow=False
        )
        self.assertEqual(response.status_code, 403)

    def test_osc_update_nonexistent_object_is_clean_404_for_admin(self):
        """Ao contrário do bug em OscListView, aqui o admin recebe um 404 de
        verdade (sem crash) porque get_object() usa get_scoped_object(), que
        chama get_object_or_404 corretamente."""
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.get(
            reverse("directorates:osc-update", kwargs={"pk": uuid.uuid4()})
        )
        self.assertEqual(response.status_code, 404)

    def test_visit_scoped_view_denied_for_user_without_access(self):
        visit = self.make_visit()
        user = make_user(role="agente", primary_directorate=self.other_directorate)
        self.client.force_login(user)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}), follow=False
        )
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)

    def test_visit_scoped_view_allowed_for_user_with_access(self):
        user = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=user)
        self.client.force_login(user)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_visit_access_denied_for_agente_not_owner_not_delegated(self):
        """VisitAccessMixin (2026-07-25): agente com acesso a diretoria mas
        sem ser dono nem delegado nao pode nem visualizar a visita alheia -
        EXCETO em Subvencao/Emendas e Fundos, onde agentes da mesma
        diretoria passaram a se enxergar/editar entre si (2026-08-19, ver
        VisitAccessMixinSubvencaoPeerTests abaixo). Usa uma diretoria fora
        desse grupo pra isolar o caso "sem nenhuma relacao especial" -
        `self.directorate`/`self.other_directorate` (as com mais OSCs no
        banco de dev real) sao ambas do grupo Subvencao/Emendas."""
        if not self.non_subvencao_directorate:
            self.skipTest("Nenhuma diretoria fora de Subvencao/Emendas e Fundos encontrada no banco de teste.")
        owner = make_user(role="agente", primary_directorate=self.non_subvencao_directorate)
        osc = self.make_osc(directorate=self.non_subvencao_directorate)
        visit = self.make_visit(osc=osc, directorate=self.non_subvencao_directorate, user=owner)
        other_agente = make_user(role="agente", primary_directorate=self.non_subvencao_directorate)
        self.client.force_login(other_agente)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_visit_access_allowed_for_delegated_agente(self):
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        delegate = make_user(role="agente", primary_directorate=self.directorate)
        FormDelegation.objects.create(id=uuid.uuid4(), visit=visit, user_id=delegate.pk, delegated_by=owner.pk)
        self.client.force_login(delegate)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_visit_access_diretor_view_only_on_others_visit(self):
        """Diretor visualiza (GET) a visita de um agente, mas nao consegue
        salvar (POST) - so visitas que ele mesmo criou sao editaveis."""
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        diretor = make_user(role="diretor", primary_directorate=self.directorate)
        self.client.force_login(diretor)
        get_response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}),
            {"status": "draft", "observacoes": "tentativa", "recomendacoes": ""},
        )
        self.assertEqual(post_response.status_code, 403)

    def test_visit_access_diretor_full_access_on_own_visit(self):
        diretor = make_user(role="diretor", primary_directorate=self.directorate)
        visit = self.make_visit(user=diretor)
        self.client.force_login(diretor)
        get_response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}),
            {"status": "draft", "observacoes": "diretor editando a propria", "recomendacoes": ""},
        )
        self.assertEqual(post_response.status_code, 302)

    def test_visit_access_admin_bypasses_ownership(self):
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_work_plan_scoped_view_denied_for_user_without_access(self):
        """Plano de Trabalho também virou admin-only pra gerenciar
        (2026-07-29) — o guard de admin em WorkPlanUpdateView.dispatch()
        bloqueia antes mesmo de checar a diretoria do plano."""
        plan = self.make_work_plan()
        user = make_user(role="agente", primary_directorate=self.other_directorate)
        self.client.force_login(user)
        response = self.client.get(
            reverse("directorates:plan-update", kwargs={"pk": plan.pk}), follow=False
        )
        self.assertEqual(response.status_code, 403)


class VisitAccessMixinSubvencaoPeerTests(DirectoratesTestBase):
    """2026-08-19, pedido explicito do usuario: "somente em monitoramento, no
    caso em emendas e fundos e subvencao, as visitas criadas por um agente da
    mesma diretoria, pode ser visto e editado por outros agentes da mesma
    diretoria (semelhante ao que o Diretor ve)". `self.directorate` (a com
    mais OSCs no banco de dev real) e "Subvencao" - usado diretamente aqui
    pra validar contra dado real, com skip se isso mudar no futuro."""

    def setUp(self):
        if not is_subvencao_directorate(self.directorate):
            self.skipTest("A diretoria com mais OSCs no banco de teste não é mais Subvenção/Emendas e Fundos.")

    def test_agente_can_view_and_edit_coworkers_visit(self):
        """Diferente do diretor (so leitura em visita alheia - ver
        test_visit_access_diretor_view_only_on_others_visit acima), o agente
        ganha edicao completa na visita de um colega da mesma diretoria."""
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        coworker = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(coworker)
        get_response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}),
            {"status": "draft", "observacoes": "colega editando", "recomendacoes": ""},
        )
        self.assertEqual(post_response.status_code, 302)

    def test_agente_still_denied_for_admin_created_visit(self):
        """Mesma exclusao ja aplicada pro diretor: visita de admin nao conta
        como "de um agente", mesmo dentro de Subvencao/Emendas e Fundos."""
        admin = make_user(role="admin")
        visit = self.make_visit(user=admin)
        agente = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(agente)
        response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_agente_sees_coworkers_visit_in_visit_list(self):
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        coworker = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(coworker)
        response = self.client.get(
            reverse("directorates:visit-list", kwargs={"pk": self.directorate.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(visit, response.context["visits"])

    def test_agente_sees_coworkers_report_in_report_list(self):
        owner = make_user(role="agente", primary_directorate=self.directorate)
        visit = self.make_visit(user=owner)
        coworker = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(coworker)
        response = self.client.get(
            reverse("directorates:report-list", kwargs={"pk": self.directorate.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(visit, response.context["visits"])

    def test_agente_sees_admin_created_visit_when_delegated(self):
        """Regressao real 2026-08-20: a exclusao de visitas admin-criadas
        (test_agente_still_denied_for_admin_created_visit acima) tinha virado
        absoluta - nem uma delegacao explicita (FormDelegation) conseguia
        furar ela, quebrando o caso de uso mais comum de delegacao (admin cria
        a visita e delega pra um agente preencher). Reportado pelo usuario em
        producao ("tentamos delegar a um agente, mas parece que nao
        funcionou")."""
        admin = make_user(role="admin")
        visit = self.make_visit(user=admin)
        agente = make_user(role="agente", primary_directorate=self.directorate)
        FormDelegation.objects.create(
            id=uuid.uuid4(), visit=visit, user_id=agente.pk, delegated_by=admin.pk,
        )
        self.client.force_login(agente)

        list_response = self.client.get(
            reverse("directorates:visit-list", kwargs={"pk": self.directorate.pk})
        )
        self.assertIn(visit, list_response.context["visits"])

        report_response = self.client.get(
            reverse("directorates:report-list", kwargs={"pk": self.directorate.pk})
        )
        self.assertIn(visit, report_response.context["visits"])

        access_response = self.client.get(
            reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        )
        self.assertEqual(access_response.status_code, 200)


class OscCrudTests(DirectoratesTestBase):
    def test_osc_create_view_forbidden_for_diretor_and_agente(self):
        """Cadastrar OSC virou admin-only (2026-07-29, decisão explícita do
        usuário) — diretor e agente perdem acesso mesmo tendo vínculo com a
        diretoria."""
        url = reverse("directorates:osc-create", kwargs={"pk": self.directorate.pk})
        for role in ("diretor", "agente"):
            user = make_user(role=role, primary_directorate=self.directorate)
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_osc_create_view_creates_osc_scoped_to_directorate(self):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = reverse("directorates:osc-create", kwargs={"pk": self.directorate.pk})
        unique_name = f"OSC Criada {uuid.uuid4().hex[:8]}"
        response = self.client.post(
            url,
            {
                "name": unique_name,
                "activity_type": "",
                "cep": "",
                "address": "",
                "number": "",
                "neighborhood": "",
                "phone": "",
                "subsidized_count": "0",
                "subsidized_type": "number",
            },
        )
        self.assertEqual(response.status_code, 302)
        osc = Osc.objects.get(name=unique_name)
        self.assertEqual(osc.directorate_id, self.directorate.pk)
        self.assertIsNotNone(osc.id)

    def test_osc_create_view_conforme_demanda_sets_subsidized_count_minus_one(self):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = reverse("directorates:osc-create", kwargs={"pk": self.directorate.pk})
        unique_name = f"OSC Demanda {uuid.uuid4().hex[:8]}"
        self.client.post(
            url,
            {
                "name": unique_name,
                "activity_type": "",
                "cep": "",
                "address": "",
                "number": "",
                "neighborhood": "",
                "phone": "",
                "subsidized_count": "0",
                "subsidized_type": "demand",
            },
        )
        osc = Osc.objects.get(name=unique_name)
        self.assertEqual(osc.subsidized_count, -1)

    def test_osc_update_view_updates_existing_osc(self):
        osc = self.make_osc(name="Nome Original")
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = reverse("directorates:osc-update", kwargs={"pk": osc.pk})
        response = self.client.post(
            url,
            {
                "name": "Nome Atualizado",
                "activity_type": "",
                "cep": "",
                "address": "",
                "number": "",
                "neighborhood": "",
                "phone": "",
                "subsidized_count": "5",
                "subsidized_type": "number",
            },
        )
        self.assertEqual(response.status_code, 302)
        osc.refresh_from_db()
        self.assertEqual(osc.name, "Nome Atualizado")
        self.assertEqual(osc.subsidized_count, 5)

    def test_osc_delete_view_forbidden_for_regular_user(self):
        osc = self.make_osc()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.post(reverse("directorates:osc-delete", kwargs={"pk": osc.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Osc.objects.filter(pk=osc.pk).exists())

    def test_osc_delete_view_allowed_for_admin(self):
        osc = self.make_osc()
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.post(reverse("directorates:osc-delete", kwargs={"pk": osc.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Osc.objects.filter(pk=osc.pk).exists())

    def test_osc_delete_view_forbidden_for_diretor(self):
        """Excluir OSC virou admin-only (2026-07-29) — diretor perdeu o
        acesso que tinha antes (era admin/diretor)."""
        osc = self.make_osc()
        diretor = make_user(role="diretor", primary_directorate=self.directorate)
        self.client.force_login(diretor)
        response = self.client.post(reverse("directorates:osc-delete", kwargs={"pk": osc.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Osc.objects.filter(pk=osc.pk).exists())


class WorkPlanCrudTests(DirectoratesTestBase):
    """WorkPlanCreateView.form_valid() ganhou `form.instance.user_id =
    self.request.user.pk` neste diff. A coluna work_plans.user_id é NOT NULL no
    banco real (confirmado via information_schema) mas o campo do model é
    `null=True, blank=True` — ou seja, sem essa linha o INSERT quebra com
    IntegrityError. Este teste teria falhado antes da correção.

    Ator trocado de agente pra admin em 2026-07-29: WorkPlanCreateView virou
    admin-only (ver OscCrudTests/WorkPlanCrudTests acima) — o teste de
    regressão do user_id continua válido, só que só é alcançável por admin
    agora."""

    def test_work_plan_create_view_forbidden_for_diretor_and_agente(self):
        url = reverse("directorates:plan-create", kwargs={"pk": self.directorate.pk})
        for role in ("diretor", "agente"):
            user = make_user(role=role, primary_directorate=self.directorate)
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_work_plan_create_view_sets_user_id_from_request_user(self):
        osc = self.make_osc()
        user = make_user(role="admin")
        self.client.force_login(user)
        url = reverse("directorates:plan-create", kwargs={"pk": self.directorate.pk})
        response = self.client.post(
            url,
            {
                "title": "Plano Novo",
                "content": "[]",
                "status": "draft",
                "osc": str(osc.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        plan = WorkPlan.objects.get(title="Plano Novo", osc=osc)
        self.assertEqual(plan.user_id, user.pk)
        self.assertEqual(plan.directorate_id, self.directorate.pk)

    def test_work_plan_create_view_works_for_user_never_in_legacy_auth_users(self):
        """Regressão do bug corrigido em 2026-07: `work_plans.user_id` tinha uma
        FK viva para o schema legado `auth.users` (Supabase), então qualquer
        usuário Django criado depois da migração original (nunca presente em
        `auth.users`) quebrava com IntegrityError ao salvar um Plano de
        Trabalho. `scripts/migrate_to_pure_pg.sql` (Passo 7) repontou a FK para
        `accounts_user`; este teste usa um usuário "puro" (nunca inserido em
        auth.users) para garantir que o fluxo funciona sem o workaround que
        existia aqui antes."""
        osc = self.make_osc()
        user = make_user(role="admin")
        self.client.force_login(user)
        url = reverse("directorates:plan-create", kwargs={"pk": self.directorate.pk})
        response = self.client.post(
            url,
            {
                "title": "Plano De Usuario Novo",
                "content": "[]",
                "status": "draft",
                "osc": str(osc.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        plan = WorkPlan.objects.get(title="Plano De Usuario Novo", osc=osc)
        self.assertEqual(plan.user_id, user.pk)

    def test_work_plan_update_view_updates_title(self):
        plan = self.make_work_plan()
        admin = make_user(role="admin")
        self.client.force_login(admin)
        url = reverse("directorates:plan-update", kwargs={"pk": plan.pk})
        response = self.client.post(
            url,
            {"title": "Titulo Editado", "content": "[]", "status": "finalized"},
        )
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.title, "Titulo Editado")
        self.assertEqual(plan.status, "finalized")

    def test_work_plan_delete_view_forbidden_for_regular_user(self):
        plan = self.make_work_plan()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.post(reverse("directorates:plan-delete", kwargs={"pk": plan.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(WorkPlan.objects.filter(pk=plan.pk).exists())

    def test_work_plan_delete_view_allowed_for_admin(self):
        plan = self.make_work_plan()
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.post(reverse("directorates:plan-delete", kwargs={"pk": plan.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WorkPlan.objects.filter(pk=plan.pk).exists())


class WorkPlanContentXssTests(DirectoratesTestBase):
    """plan_form.html injetava `{{ object.content|default:"[]"|safe }}` cru
    dentro de um <script> (XSS confirmado, 2026-07-29) — trocado por
    `plan_content_json|json_script:"plan-content-data"` + JSON.parse. Um
    `content` malicioso não deve conseguir fechar a tag <script> nem
    executar como HTML/JS fora do JSON."""

    PAYLOAD = [{"text": "</script><script>window.__xss=1</script>"}]

    def test_malicious_content_does_not_break_out_of_script_tag(self):
        plan = self.make_work_plan()
        plan.content = self.PAYLOAD
        plan.save()
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.get(reverse("directorates:plan-update", kwargs={"pk": plan.pk}))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("<script>window.__xss=1</script>", html)
        self.assertIn('id="plan-content-data"', html)
        self.assertIn("JSON.parse", html)


class VisitFlowTests(DirectoratesTestBase):
    def test_visit_create_view_draft_flow(self):
        osc = self.make_osc()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        url = reverse("directorates:visit-create", kwargs={"pk": self.directorate.pk})
        response = self.client.post(
            url,
            {
                "osc": str(osc.pk),
                "status": "draft",
                "identificacao[visit_date_1]": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        visit = Visit.objects.filter(osc=osc, directorate=self.directorate).latest("created_at")
        self.assertEqual(visit.status, "draft")
        self.assertEqual(visit.identificacao.get("registered_by_username"), user.get_username())
        self.assertEqual(visit.user_id, user.pk)

    def test_visit_create_view_owner_can_access_own_visit_afterwards(self):
        """Regressao 2026-07-25: VisitCreateView nao setava user_id, entao o
        agente que acabou de criar a visita ficava bloqueado (403) ao tentar
        abrir o proprio instrumental logo em seguida - VisitAccessMixin exige
        dono/delegado. Reportado pelo usuario em producao/dev apos o deploy."""
        osc = self.make_osc()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        create_url = reverse("directorates:visit-create", kwargs={"pk": self.directorate.pk})
        self.client.post(
            create_url,
            {
                "osc": str(osc.pk),
                "status": "draft",
                "identificacao[visit_date_1]": date.today().isoformat(),
            },
        )
        visit = Visit.objects.filter(osc=osc, directorate=self.directorate).latest("created_at")
        response = self.client.get(reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk}))
        self.assertEqual(response.status_code, 200)

    def test_visit_create_view_without_osc_shows_error_and_redirects_back(self):
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        url = reverse("directorates:visit-create", kwargs={"pk": self.directorate.pk})
        response = self.client.post(url, {"status": "draft"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("directorates:visit-create", kwargs={"pk": self.directorate.pk}),
            response.url,
        )

    def test_visit_delete_view_forbidden_for_regular_user(self):
        visit = self.make_visit()
        user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(user)
        response = self.client.post(reverse("directorates:visit-delete", kwargs={"pk": visit.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Visit.objects.filter(pk=visit.pk).exists())

    def test_visit_delete_view_allowed_for_admin(self):
        visit = self.make_visit()
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.post(reverse("directorates:visit-delete", kwargs={"pk": visit.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())


class VisitDelegateViewTests(DirectoratesTestBase):
    """Ator trocado de diretor pra admin nestes testes (2026-08-20) - estavam
    desatualizados desde o commit 191e915 (2026-08-16), que restringiu
    VisitDelegateView.dispatch() de "admin ou diretor" pra admin-only; os
    testes que esperavam 302 pra um diretor delegando estavam falhando
    silenciosamente há um mês (confirmado rodando a suite antes desta
    correção)."""

    def test_delegate_to_users_creates_form_delegations(self):
        visit = self.make_visit()
        admin = make_user(role="admin")
        target_user = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(admin)
        url = reverse("directorates:visit-delegate", kwargs={"pk": visit.pk})
        response = self.client.post(url, {"user_ids": [str(target_user.pk)]})
        self.assertEqual(response.status_code, 302)
        delegation = FormDelegation.objects.get(visit=visit, user_id=target_user.pk)
        self.assertEqual(delegation.delegated_by, admin.pk)

    def test_delegate_replaces_previous_delegations(self):
        visit = self.make_visit()
        admin = make_user(role="admin")
        first_target = make_user(role="agente", primary_directorate=self.directorate)
        second_target = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(admin)
        url = reverse("directorates:visit-delegate", kwargs={"pk": visit.pk})

        self.client.post(url, {"user_ids": [str(first_target.pk)]})
        self.assertEqual(FormDelegation.objects.filter(visit=visit).count(), 1)

        self.client.post(url, {"user_ids": [str(second_target.pk)]})
        delegations = FormDelegation.objects.filter(visit=visit)
        self.assertEqual(delegations.count(), 1)
        self.assertEqual(delegations.first().user_id, second_target.pk)

    def test_delegate_denied_for_diretor_role(self):
        """VisitDelegateView (2026-08-16): delegar virou admin-only - antes
        diretor tambem podia, agora nao pode mais, mesmo sendo diretor da
        mesma diretoria da visita (acesso a diretoria nao é o que bloqueia
        aqui - é o papel)."""
        visit = self.make_visit()
        diretor = make_user(role="diretor", primary_directorate=self.directorate)
        self.client.force_login(diretor)
        url = reverse("directorates:visit-delegate", kwargs={"pk": visit.pk})
        response = self.client.post(url, {"user_ids": []})
        self.assertEqual(response.status_code, 403)

    def test_delegate_denied_for_agente_role(self):
        """VisitDelegateView (2026-07-25, reforçado 2026-08-16): só admin
        pode delegar, mesmo um agente com acesso normal à diretoria não
        pode."""
        visit = self.make_visit()
        agente = make_user(role="agente", primary_directorate=self.directorate)
        self.client.force_login(agente)
        url = reverse("directorates:visit-delegate", kwargs={"pk": visit.pk})
        response = self.client.post(url, {"user_ids": []})
        self.assertEqual(response.status_code, 403)


@override_settings(STORAGES=STATIC_TEST_STORAGES)
class DirectorateDetailViewRedirectTests(TestCase):
    """DirectorateDetailView.get() nunca renderiza a própria página: sempre
    redireciona para o módulo específico com base no nome (sem acento) da
    diretoria. Esse roteamento não foi alterado neste diff, mas é o fluxo
    "home via dir_slug" mais importante do app."""

    def _get_as_admin(self, directorate):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        return self.client.get(reverse("directorates:detail", kwargs={"pk": directorate.pk}))

    def test_cras_directorate_redirects_to_cras_home(self):
        directorate = Directorate.objects.filter(name__iexact="CRAS").first()
        if not directorate:
            self.skipTest("Diretoria 'CRAS' não encontrada no banco de teste.")
        response = self._get_as_admin(directorate)
        self.assertRedirects(
            response,
            reverse("cras:home", kwargs={"pk": directorate.pk}),
            fetch_redirect_response=False,
        )

    def test_monitoring_directorate_redirects_to_monitoramento_home(self):
        directorate = Directorate.objects.filter(name__iexact="Outros").first()
        if not directorate:
            self.skipTest("Diretoria 'Outros' não encontrada no banco de teste.")
        response = self._get_as_admin(directorate)
        self.assertRedirects(
            response,
            reverse("monitoramento:home", kwargs={"pk": directorate.pk}),
            fetch_redirect_response=False,
        )


class WorkPlanObjectivesAndVisitLinkTests(DirectoratesTestBase):
    """Feature 2026-07 (Emendas e Fundos): os textos 'Objeto do Relatório' e
    item 2 A/B/C do relatório de visita passam a viver no plano de trabalho
    (WorkPlanObjectivesView), a visita guarda o plano vinculado
    (visits.work_plan_id) — auto-selecionado quando a OSC tem um único plano —
    e o VisitReportView herda os textos do plano com fallback para a OSC."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.emendas = Directorate.objects.filter(name__icontains="emenda").first()

    def setUp(self):
        if not self.emendas:
            self.skipTest("Diretoria 'Emendas e Fundos' não encontrada no banco de teste.")

    def _login_admin(self):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        return admin

    def _create_visit_via_post(self, osc, extra=None):
        url = reverse("directorates:visit-create", kwargs={"pk": osc.directorate.pk})
        payload = {
            "osc": str(osc.pk),
            "status": "draft",
            "identificacao[visit_date_1]": date.today().isoformat(),
        }
        payload.update(extra or {})
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 302)
        return Visit.objects.filter(osc=osc).latest("created_at")

    def test_plan_objectives_post_saves_the_four_fields(self):
        osc = self.make_osc(directorate=self.emendas)
        plan = self.make_work_plan(osc=osc, directorate=self.emendas)
        self._login_admin()
        url = reverse("directorates:plan-objectives", kwargs={"pk": plan.pk})
        response = self.client.post(
            url,
            {
                "objeto": "Objeto do relatório do plano",
                "objetivos": "Texto dos objetivos",
                "metas": "Texto das metas",
                "atividades": "Texto das atividades",
            },
        )
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.objeto, "Objeto do relatório do plano")
        self.assertEqual(plan.objetivos, "Texto dos objetivos")
        self.assertEqual(plan.metas, "Texto das metas")
        self.assertEqual(plan.atividades, "Texto das atividades")

    def test_plan_objectives_denied_for_user_without_directorate_access(self):
        osc = self.make_osc(directorate=self.emendas)
        plan = self.make_work_plan(osc=osc, directorate=self.emendas)
        outsider_directorate = Directorate.objects.exclude(pk=self.emendas.pk).order_by("name").first()
        outsider = make_user(role="agente", primary_directorate=outsider_directorate)
        self.client.force_login(outsider)
        url = reverse("directorates:plan-objectives", kwargs={"pk": plan.pk})
        response = self.client.post(url, {"objeto": "hack"}, follow=False)
        self.assertRedirects(response, reverse("core:landing"), fetch_redirect_response=False)
        plan.refresh_from_db()
        self.assertEqual(plan.objeto, "")

    def test_visit_create_auto_links_single_work_plan(self):
        osc = self.make_osc(directorate=self.emendas)
        plan = self.make_work_plan(osc=osc, directorate=self.emendas)
        self._login_admin()
        visit = self._create_visit_via_post(osc)
        self.assertEqual(visit.work_plan_id, plan.pk)

    def test_visit_create_uses_chosen_plan_when_osc_has_multiple(self):
        osc = self.make_osc(directorate=self.emendas)
        self.make_work_plan(osc=osc, directorate=self.emendas)
        plan_b = self.make_work_plan(osc=osc, directorate=self.emendas)
        self._login_admin()
        visit = self._create_visit_via_post(osc, {"work_plan": str(plan_b.pk)})
        self.assertEqual(visit.work_plan_id, plan_b.pk)

    def test_visit_create_with_multiple_plans_and_no_choice_links_none(self):
        osc = self.make_osc(directorate=self.emendas)
        self.make_work_plan(osc=osc, directorate=self.emendas)
        self.make_work_plan(osc=osc, directorate=self.emendas)
        self._login_admin()
        visit = self._create_visit_via_post(osc)
        self.assertIsNone(visit.work_plan_id)

    def test_visit_create_ignores_plan_belonging_to_another_osc(self):
        osc = self.make_osc(directorate=self.emendas)
        self.make_work_plan(osc=osc, directorate=self.emendas)
        self.make_work_plan(osc=osc, directorate=self.emendas)
        other_osc = self.make_osc(name="Outra OSC", directorate=self.emendas)
        foreign_plan = self.make_work_plan(osc=other_osc, directorate=self.emendas)
        self._login_admin()
        visit = self._create_visit_via_post(osc, {"work_plan": str(foreign_plan.pk)})
        self.assertIsNone(visit.work_plan_id)

    def test_visit_create_outside_emendas_links_no_plan(self):
        non_emendas = (
            Directorate.objects.exclude(name__icontains="emenda")
            .exclude(name__icontains="fundo")
            .filter(name__iexact="Outros")
            .first()
        )
        if not non_emendas:
            self.skipTest("Diretoria 'Outros' não encontrada no banco de teste.")
        osc = self.make_osc(directorate=non_emendas)
        self.make_work_plan(osc=osc, directorate=non_emendas)
        self._login_admin()
        visit = self._create_visit_via_post(osc)
        self.assertIsNone(visit.work_plan_id)

    def test_report_inherits_texts_from_linked_plan(self):
        osc = self.make_osc(directorate=self.emendas)
        osc.objeto = "Objeto da OSC"
        osc.objetivos = "Objetivos da OSC"
        osc.save()
        plan = self.make_work_plan(osc=osc, directorate=self.emendas)
        plan.objeto = "Objeto do plano"
        plan.objetivos = "Objetivos do plano"
        plan.metas = "Metas do plano"
        plan.atividades = "Atividades do plano"
        plan.save()
        visit = self.make_visit(osc=osc, directorate=self.emendas)
        visit.work_plan = plan
        visit.save()
        self._login_admin()
        url = reverse(
            "directorates:visit-report",
            kwargs={"pk": visit.pk, "report_type": "parecer_tecnico"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        report_data = response.context["report_data"]
        self.assertEqual(report_data["objeto_relatorio"], "Objeto do plano")
        self.assertEqual(report_data["item2_a_objetivos"], "Objetivos do plano")
        self.assertEqual(report_data["item2_b_metas"], "Metas do plano")
        self.assertEqual(report_data["item2_c_atividades"], "Atividades do plano")

    def test_report_falls_back_to_osc_text_when_plan_field_is_empty(self):
        osc = self.make_osc(directorate=self.emendas)
        osc.objeto = "Objeto da OSC"
        osc.save()
        plan = self.make_work_plan(osc=osc, directorate=self.emendas)
        plan.objetivos = "Objetivos do plano"
        plan.save()
        visit = self.make_visit(osc=osc, directorate=self.emendas)
        visit.work_plan = plan
        visit.save()
        self._login_admin()
        url = reverse(
            "directorates:visit-report",
            kwargs={"pk": visit.pk, "report_type": "parecer_tecnico"},
        )
        response = self.client.get(url)
        report_data = response.context["report_data"]
        self.assertEqual(report_data["objeto_relatorio"], "Objeto da OSC")
        self.assertEqual(report_data["item2_a_objetivos"], "Objetivos do plano")

    def test_report_without_linked_plan_keeps_using_osc_texts(self):
        osc = self.make_osc(directorate=self.emendas)
        osc.objeto = "Objeto da OSC"
        osc.save()
        visit = self.make_visit(osc=osc, directorate=self.emendas)
        self._login_admin()
        url = reverse(
            "directorates:visit-report",
            kwargs={"pk": visit.pk, "report_type": "parecer_tecnico"},
        )
        response = self.client.get(url)
        report_data = response.context["report_data"]
        self.assertEqual(report_data["objeto_relatorio"], "Objeto da OSC")


@override_settings(STORAGES=STATIC_TEST_STORAGES)
class DirectorateListViewTests(TestCase):
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("directorates:list"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_admin_sees_all_directorates(self):
        admin = make_user(role="admin")
        self.client.force_login(admin)
        response = self.client.get(reverse("directorates:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["directorates"]), list(Directorate.objects.order_by("name"))
        )

    def test_regular_user_sees_only_linked_directorates(self):
        directorate = Directorate.objects.first()
        user = make_user(role="user", primary_directorate=directorate)
        self.client.force_login(user)
        response = self.client.get(reverse("directorates:list"))
        self.assertEqual(response.status_code, 200)
        seen = list(response.context["directorates"])
        self.assertEqual(seen, [directorate])

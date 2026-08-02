import uuid

from django.db import models
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.ceai.models import Submission
from apps.directorates.models import Directorate, MonthlyReport, MonthlySubmission


def unique_username(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class CeaiTestDataMixin:
    """Cria usuários/diretorias reaproveitados pelos testes deste módulo.

    Roda contra o banco de dev real (managed=False); tudo é criado em
    métodos de teste dentro de TestCase, portanto revertido por rollback
    automático ao final de cada teste.
    """

    @classmethod
    def setUpTestData(cls):
        cls.ceai_directorate = Directorate.objects.get(name="CEAI")
        # Qualquer outra diretoria existente, usada para provar que a
        # CeaiMonthlyNarrativeView ignora o pk vindo da URL.
        cls.other_directorate = Directorate.objects.exclude(pk=cls.ceai_directorate.pk).first()

        cls.admin = User.objects.create_superuser(
            username=unique_username("ceai_admin"),
            email=f"{unique_username('ceai_admin')}@example.com",
            password="testpass123",
        )

        # Usuário autenticado, mas sem NENHUM vínculo com a diretoria CEAI
        # (nem primary_directorate, nem ProfileDirectorate) -> deve ser
        # barrado pelo DirectorateAccessMixin antes mesmo do RoleRequiredMixin.
        cls.outsider = User.objects.create_user(
            username=unique_username("ceai_outsider"),
            email=f"{unique_username('ceai_outsider')}@example.com",
            password="testpass123",
        )
        Profile.objects.create(user=cls.outsider, role="agente")

        # Usuário com acesso à diretoria CEAI (primary_directorate), mas com
        # role fora de allowed_roles das views -> deve ser barrado pelo
        # RoleRequiredMixin (depois de passar no DirectorateAccessMixin).
        cls.wrong_role_user = User.objects.create_user(
            username=unique_username("ceai_wrongrole"),
            email=f"{unique_username('ceai_wrongrole')}@example.com",
            password="testpass123",
        )
        Profile.objects.create(
            user=cls.wrong_role_user, role="user", primary_directorate=cls.ceai_directorate
        )

        # monthly_reports.user_id (db_column do field user_external_id) ainda
        # carrega uma FK física para o schema legado "auth.users" (resíduo da
        # migração Supabase, ver CLAUDE.md). Usuários Django criados DEPOIS
        # da migração -- como os de cima -- não existem em auth.users e
        # violam essa FK ao criar um MonthlyReport novo. Para os testes que
        # efetivamente gravam um MonthlyReport, usamos um usuário real já
        # existente (um dos migrados de auth.users) com profile role=admin,
        # somente leitura -- nenhuma linha é criada/alterada nessas tabelas.
        legacy_admin_profile = Profile.objects.filter(role="admin").select_related("user").first()
        cls.legacy_admin = legacy_admin_profile.user if legacy_admin_profile else cls.admin


class CeaiAccessControlTests(CeaiTestDataMixin, TestCase):
    def test_dashboard_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("ceai:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_dashboard_accessible_to_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("ceai:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_denies_user_without_directorate_access(self):
        # DirectorateAccessMixin.dispatch roda ANTES do RoleRequiredMixin
        # (ver MRO de CeaiDashboardView) e redireciona para core:landing
        # ("/", que por sua vez é um RedirectView para /mapas/ -- por isso
        # não seguimos o redirect com assertRedirects, que esperaria 200).
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("ceai:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:landing"))

    def test_dashboard_denies_user_with_wrong_role(self):
        # Este usuário TEM acesso à diretoria (primary_directorate=CEAI),
        # então passa pelo DirectorateAccessMixin; quem barra é o
        # RoleRequiredMixin, cujo AccessMixin.handle_no_permission levanta
        # PermissionDenied (403) para usuários já autenticados, em vez de
        # redirecionar.
        self.client.force_login(self.wrong_role_user)
        response = self.client.get(reverse("ceai:dashboard"))
        self.assertEqual(response.status_code, 403)


class CeaiMonthlyNarrativeViewTests(CeaiTestDataMixin, TestCase):
    def setUp(self):
        # Usa um usuário real pré-existente (legacy_admin) porque estes
        # testes de POST gravam MonthlyReport.user_external_id, cuja coluna
        # física ainda tem FK para o schema legado auth.users (ver nota em
        # setUpTestData) -- um usuário recém-criado pelo teste violaria essa
        # FK.
        self.client.force_login(self.legacy_admin)

    def test_get_ignores_url_pk_and_always_uses_ceai_directorate(self):
        # Passa o pk (UUID) de uma diretoria QUALQUER OUTRA na URL: a view
        # deve ignorá-lo e resolver sempre para a diretoria CEAI.
        # (Nota: usar aqui o *slug* da outra diretoria em vez do pk faria
        # reverse() explodir -- ver bug de DirectorateSlugConverter.to_url
        # relatado no resumo final.)
        url = reverse(
            "ceai:ceai_monthly_report", kwargs={"pk": self.other_directorate.pk}
        )
        response = self.client.get(url, {"month": 5, "year": 2024})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.ceai_directorate.pk)

    def test_get_also_ignores_ceai_own_uuid_passed_directly(self):
        # Mesmo passando o pk correto (UUID da própria CEAI) o resultado deve
        # ser idêntico -- a view não deveria depender do valor da URL.
        url = reverse("ceai:ceai_monthly_report", kwargs={"pk": self.ceai_directorate.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.ceai_directorate.pk)

    def test_post_creates_monthly_report_with_user_external_id(self):
        # Antes da correção, o código usava a chave "user_id" em
        # update_or_create(defaults=...), que não existe como nome de campo
        # em MonthlyReport (o field se chama user_external_id, com
        # db_column="user_id") -- isso levantava TypeError. Este teste
        # cobre a regressão. A criação/edição agora passa pelo editor
        # (CeaiNarrativeEditorView), que grava content_html sanitizado.
        url = reverse(
            "ceai:narrative-editor", kwargs={"pk": self.other_directorate.pk}
        )
        response = self.client.post(
            url, {"month": 6, "year": 2024, "content_html": "<p>Relatorio narrativo de teste CEAI</p>"}
        )
        self.assertEqual(response.status_code, 302)

        report = MonthlyReport.objects.get(
            directorate=self.ceai_directorate, setor="ceai", month=6, year=2024
        )
        self.assertEqual(report.user_external_id, self.legacy_admin.id)
        self.assertEqual(report.status, "finalized")
        self.assertEqual(report.content, "<p>Relatorio narrativo de teste CEAI</p>")

    def test_post_updates_existing_report_instead_of_duplicating(self):
        url = reverse(
            "ceai:narrative-editor", kwargs={"pk": self.ceai_directorate.pk}
        )
        self.client.post(url, {"month": 7, "year": 2024, "content_html": "<p>Primeira versao</p>"})
        self.client.post(url, {"month": 7, "year": 2024, "content_html": "<p>Versao atualizada</p>"})

        reports = MonthlyReport.objects.filter(
            directorate=self.ceai_directorate, setor="ceai", month=7, year=2024
        )
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().content, "<p>Versao atualizada</p>")


class CeaiSubmissionModelTests(CeaiTestDataMixin, TestCase):
    def test_submission_shares_physical_table_with_monthly_submission(self):
        sub = Submission.objects.create(
            user=self.admin,
            directorate_id=self.ceai_directorate.pk,
            month=3,
            year=2025,
            data={"_setor": "ceai", "hello": "world"},
        )
        # Mesmo id, mesma tabela física ('submissions') -- deve ser visível
        # via o outro model que aponta para essa tabela.
        same_row = MonthlySubmission.objects.get(pk=sub.pk)
        self.assertEqual(same_row.month, 3)
        self.assertEqual(same_row.year, 2025)
        self.assertEqual(same_row.directorate_id, self.ceai_directorate.pk)
        self.assertEqual(same_row.data, {"_setor": "ceai", "hello": "world"})

    def test_user_and_directorate_id_are_nullable(self):
        # Antes desta mudança user/directorate_id eram obrigatórios; a
        # migração para a tabela compartilhada 'submissions' exigiu
        # torná-los opcionais.
        sub = Submission.objects.create(
            user=None,
            directorate_id=None,
            month=1,
            year=2025,
            data={},
        )
        sub.refresh_from_db()
        self.assertIsNone(sub.user_id)
        self.assertIsNone(sub.directorate_id)

    def test_user_field_configured_as_set_null(self):
        # Cobre a mudança de on_delete=CASCADE -> SET_NULL em Submission.user.
        # Não exercitamos um User.delete() de verdade aqui: apagar qualquer
        # User neste banco de dev dispara o Collector de FKs reversas de
        # TODOS os apps (inclusive apps.poprua, ainda em desenvolvimento),
        # e pelo menos um deles (creas_pop_rua_reports.created_by) tem um
        # descompasso de tipo de coluna que quebra esse cascade com
        # "operator does not exist: text = uuid" -- um bug real, porém
        # totalmente alheio ao escopo ceai/creasidoso desta sessão. Testamos
        # a configuração do campo diretamente para não depender disso.
        field = Submission._meta.get_field("user")
        self.assertTrue(field.null)
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)


class CeaiUpdateDataViewTests(CeaiTestDataMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_get_renders_form_for_territorial_unit(self):
        url = reverse("ceai:update_data", kwargs={"unit": "Brasil"})
        response = self.client.get(url, {"month": 4, "year": 2025})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["unit"], "Brasil")

    def test_post_creates_submission_linked_to_ceai_directorate(self):
        url = reverse("ceai:update_data", kwargs={"unit": "Morumbi"})
        response = self.client.post(
            url,
            {
                "month": 8,
                "year": 2025,
                "inseridos_masc": "3",
                "inseridos_fem": "2",
            },
        )
        self.assertRedirects(response, reverse("ceai:dashboard"))

        submission = Submission.objects.get(directorate_id=self.ceai_directorate.pk, month=8, year=2025)
        self.assertTrue(submission.data.get("_is_multi_unit"))
        self.assertIn("Morumbi", submission.data["units"])
        self.assertEqual(submission.data["units"]["Morumbi"].get("inseridos_masc"), "3")


class CeaiDashboardAndListViewsTests(CeaiTestDataMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_dashboard_lists_existing_submissions_without_error(self):
        response = self.client.get(reverse("ceai:dashboard"), {"year": 2025})
        self.assertEqual(response.status_code, 200)
        self.assertIn("summary", response.context)

    def test_monthly_report_view_includes_history(self):
        url = reverse("ceai:ceai_monthly_report", kwargs={"pk": self.ceai_directorate.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.ceai_directorate.pk)
        self.assertIn("history", response.context)

    def test_data_list_view(self):
        response = self.client.get(reverse("ceai:data_list"), {"year": 2025})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.ceai_directorate.pk)

    def test_oficinas_view(self):
        response = self.client.get(reverse("ceai:oficinas", kwargs={"unit": "Brasil"}))
        self.assertEqual(response.status_code, 200)

    def test_categories_view(self):
        response = self.client.get(reverse("ceai:categories", kwargs={"unit": "Brasil"}))
        self.assertEqual(response.status_code, 200)

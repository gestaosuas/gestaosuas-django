import uuid

from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.creasidoso.models import CreasIdosoReport, CreasPcdReport
from apps.creasidoso.views import CreasIdosoQuickEditView, CreasPcdQuickEditView
from apps.directorates.models import Directorate


def unique_username(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class CreasIdosoTestDataMixin:
    """Roda contra o banco de dev real (managed=False). Tudo criado dentro
    de métodos de teste é revertido por rollback automático (TestCase)."""

    @classmethod
    def setUpTestData(cls):
        cls.directorate = Directorate.objects.get(name__icontains="CREAS")

        cls.admin = User.objects.create_superuser(
            username=unique_username("creas_admin"),
            email=f"{unique_username('creas_admin')}@example.com",
            password="testpass123",
        )

        cls.viewer = User.objects.create_user(
            username=unique_username("creas_viewer"),
            email=f"{unique_username('creas_viewer')}@example.com",
            password="testpass123",
        )
        Profile.objects.create(
            user=cls.viewer, role="agente", primary_directorate=cls.directorate
        )

        # creas_idoso_reports.created_by / creas_pcd_reports.created_by ainda
        # carregam uma FK física para o schema legado "auth.users" (residuo
        # da migracao Supabase, ver CLAUDE.md). Usuarios Django criados
        # DEPOIS da migracao (como os que criamos acima para login) não
        # existem em auth.users e violam essa FK. Para exercitar o caminho
        # de "update" de um relatorio já existente, usamos o id de um
        # usuário real pré-existente (um dos 50 migrados de auth.users),
        # só leitura -- nenhuma linha é criada/alterada nessa tabela.
        cls.legacy_user_id = (
            User.objects.exclude(id__in=[cls.admin.id, cls.viewer.id])
            .values_list("id", flat=True)
            .first()
        )


class CreasIdosoUrlOrderingTests(CreasIdosoTestDataMixin, TestCase):
    """Cobre a correção de ordenação das rotas quick-edit-*: elas precisam
    ser resolvidas ANTES de <dir_slug:pk>/, senão o converter dir_slug
    (regex [\\w-]+) captura "quick-edit-idoso"/"quick-edit-pcd" como se
    fossem o slug de uma diretoria."""

    def test_quick_edit_idoso_resolves_to_correct_view(self):
        match = resolve("/creasidoso/quick-edit-idoso/")
        self.assertIs(match.func.view_class, CreasIdosoQuickEditView)

    def test_quick_edit_pcd_resolves_to_correct_view(self):
        match = resolve("/creasidoso/quick-edit-pcd/")
        self.assertIs(match.func.view_class, CreasPcdQuickEditView)

    def test_quick_edit_idoso_url_reachable_end_to_end(self):
        # Sanity check funcional: sem a correção de ordenação, esta
        # requisição cairia na CreasHomeView com pk="quick-edit-idoso"
        # (não resolvido pelo converter) e retornaria 404, em vez de
        # processar o quick-edit.
        self.client.force_login(self.admin)
        report = CreasIdosoReport.objects.create(
            directorate=self.directorate, month=1, year=2099, paefi_novos_casos=0,
            created_by=self.legacy_user_id, created_at=timezone.now(), updated_at=timezone.now(),
        )
        url = reverse("creasidoso:quick-edit-idoso")
        response = self.client.post(
            url,
            {
                "sub_id": str(report.id),
                "key": "paefi_novos_casos",
                "value": "7",
                "month": 1,
                "year": 2099,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")


class CreasSharedQuickEditViewTests(CreasIdosoTestDataMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_denies_non_admin(self):
        # allowed_roles = ["admin"]; RoleRequiredMixin (AccessMixin puro, sem
        # LoginRequiredMixin) levanta PermissionDenied (403) para usuário já
        # autenticado com role não permitida, em vez de redirecionar.
        self.client.force_login(self.viewer)
        url = reverse("creasidoso:quick-edit-idoso")
        response = self.client.post(
            url,
            {"sub_id": "", "key": "paefi_novos_casos", "value": "1", "month": 2, "year": 2099},
        )
        self.assertEqual(response.status_code, 403)

    def test_rejects_non_numeric_field_key(self):
        # A checagem de allowed_keys roda ANTES do get_or_create, então este
        # caminho nao é afetado pelo bug de "updated_at" descrito abaixo.
        url = reverse("creasidoso:quick-edit-idoso")
        response = self.client.post(
            url,
            {"sub_id": "", "key": "status", "value": "1", "month": 3, "year": 2099},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_creating_new_report_via_quick_edit_succeeds(self):
        # Regressão do bug corrigido em 2026-07 (apps/creasidoso/views.py,
        # CreasSharedQuickEditView.post): quando sub_id não é informado (caso
        # de criação de um relatório novo), o get_or_create() não incluía
        # "updated_at" nos defaults, mas a coluna é NOT NULL sem default no
        # banco — o INSERT quebrava com IntegrityError. Agora os defaults
        # incluem updated_at; este teste confirma que a criação funciona.
        self.assertFalse(
            CreasIdosoReport.objects.filter(directorate=self.directorate, month=4, year=2099).exists()
        )
        url = reverse("creasidoso:quick-edit-idoso")
        response = self.client.post(
            url,
            {"sub_id": "", "key": "paefi_novos_casos", "value": "5", "month": 4, "year": 2099},
        )
        self.assertEqual(response.status_code, 200)
        report = CreasIdosoReport.objects.get(directorate=self.directorate, month=4, year=2099)
        self.assertEqual(report.paefi_novos_casos, 5)
        self.assertIsNotNone(report.updated_at)

    def test_creating_new_pcd_report_via_quick_edit_succeeds(self):
        # Mesmo cenário do teste acima, para o outro model (CreasPcdReport) --
        # confirma que a correção vale para o CreasSharedQuickEditView.post
        # genérico e não é específica de um subclass.
        url = reverse("creasidoso:quick-edit-pcd")
        response = self.client.post(
            url,
            {
                "sub_id": "",
                "key": "def_violencia_fisica_total",
                "value": "2",
                "month": 6,
                "year": 2099,
            },
        )
        self.assertEqual(response.status_code, 200)
        report = CreasPcdReport.objects.get(directorate=self.directorate, month=6, year=2099)
        self.assertEqual(report.def_violencia_fisica_total, 2)
        self.assertIsNotNone(report.updated_at)

    def test_updates_existing_report_and_bumps_updated_at(self):
        original_updated_at = timezone.make_aware(timezone.datetime(2020, 1, 1, 12, 0, 0))
        report = CreasIdosoReport.objects.create(
            directorate=self.directorate, month=5, year=2099, paefi_novos_casos=1,
            created_by=self.legacy_user_id, created_at=original_updated_at, updated_at=original_updated_at,
        )

        url = reverse("creasidoso:quick-edit-idoso")
        response = self.client.post(
            url,
            {
                "sub_id": str(report.id),
                "key": "paefi_novos_casos",
                "value": "9",
                "month": 5,
                "year": 2099,
            },
        )
        self.assertEqual(response.status_code, 200)

        report.refresh_from_db()
        self.assertEqual(report.paefi_novos_casos, 9)
        # report.updated_at = datetime.now() é setado explicitamente antes do
        # save() (mudança coberta por este teste) -- deve avançar em relação
        # ao valor antigo, sem depender de auto_now (o model não usa).
        self.assertGreater(report.updated_at, original_updated_at)


class CreasHomeViewTests(CreasIdosoTestDataMixin, TestCase):
    # Nota: usamos self.directorate.pk (UUID) e não .slug nestas reverse()
    # porque DirectorateSlugConverter.to_url() quebra com ValidationError não
    # tratada quando recebe uma string que não é UUID (ver bug relatado no
    # resumo final) -- isso vale para QUALQUER slug, não só para nomes com
    # problema de encoding.

    def test_home_requires_login(self):
        url = reverse("creasidoso:home", kwargs={"pk": self.directorate.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_home_accessible_with_directorate_access(self):
        self.client.force_login(self.viewer)
        url = reverse("creasidoso:home", kwargs={"pk": self.directorate.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directorate"].pk, self.directorate.pk)

    def test_home_denies_user_without_directorate_access(self):
        outsider = User.objects.create_user(
            username=unique_username("creas_outsider"),
            email=f"{unique_username('creas_outsider')}@example.com",
            password="testpass123",
        )
        Profile.objects.create(user=outsider, role="agente")
        self.client.force_login(outsider)
        url = reverse("creasidoso:home", kwargs={"pk": self.directorate.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:landing"))

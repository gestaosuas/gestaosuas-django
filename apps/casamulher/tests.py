import uuid

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.directorates.models import Directorate

from .models import CasaDaMulherReport


def make_directorate(name=None):
    """Diretoria nova e isolada (tabela managed=False, id sem default automatico)."""
    return Directorate.objects.create(
        id=uuid.uuid4(),
        name=name or f"Diretoria Teste {uuid.uuid4().hex[:8]}",
    )


def make_user(email=None, password="senha12345", role=Profile.ROLE_ADMIN, full_name="Usuario Teste"):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(username=email, email=email, password=password)
    profile = Profile.objects.create(user=user, full_name=full_name, role=role)
    return user, profile


def get_existing_admin():
    """
    Retorna um Profile admin ja existente no banco de dev.

    Nao usamos um usuario recem-criado para os testes que gravam user_id: a coluna
    casa_da_mulher_reports.user_id (NOT NULL) ainda tem uma FK legada apontando
    para o schema Supabase residual `auth.users` (nao para accounts_user) neste
    banco de dev — confirmado via pg_constraint. O id de um User Django recem
    criado nao existe em auth.users e viola essa constraint com IntegrityError.
    Um admin ja migrado do Supabase satisfaz a FK.
    """
    return Profile.objects.filter(role=Profile.ROLE_ADMIN).select_related("user").first()


class CasaMulherSharedQuickEditViewTests(TestCase):
    """
    Cobre o comportamento alterado em CasaMulherSharedQuickEditView:
    - get_or_create agora recebe defaults={"user_id", "created_by"} ao criar um
      relatorio novo (evita relatorio criado sem esses campos antes do save() explicito).
    - created_by/user_id sao sempre sobrescritos com o usuario autenticado, mesmo
      em relatorios ja existentes (via sub_id).
    """

    def setUp(self):
        self.admin_profile = get_existing_admin()
        self.assertIsNotNone(self.admin_profile, "Nenhum profile admin encontrado no banco de dev — pré-requisito do teste.")
        self.admin_user = self.admin_profile.user
        self.directorate = make_directorate()
        self.url = reverse("casamulher:quick-edit-casa-da-mulher")

    def _login_admin(self):
        self.client.force_login(self.admin_user)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.post(self.url, {
            "directorate_id": str(self.directorate.pk),
            "key": "cm_atend_mulheres_atendidas",
            "value": "5",
            "month": "1",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_user_forbidden(self):
        regular_email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        password = "senha12345"
        make_user(email=regular_email, password=password, role=Profile.ROLE_USER)
        self.client.login(username=regular_email, password=password)
        response = self.client.post(self.url, {
            "directorate_id": str(self.directorate.pk),
            "key": "cm_atend_mulheres_atendidas",
            "value": "5",
            "month": "1",
            "year": "2031",
        })
        self.assertIn(response.status_code, (302, 403))

    def test_creates_new_report_with_user_id_and_created_by_populated(self):
        self._login_admin()
        response = self.client.post(self.url, {
            "directorate_id": str(self.directorate.pk),
            "key": "cm_atend_mulheres_atendidas",
            "value": "5",
            "month": "1",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        report = CasaDaMulherReport.objects.get(directorate=self.directorate, month=1, year=2031)
        self.assertEqual(report.cm_atend_mulheres_atendidas, 5)
        self.assertEqual(report.user_id, self.admin_user.pk)
        self.assertEqual(report.created_by, self.admin_user.email)

    def test_updating_existing_report_via_sub_id_overwrites_created_by(self):
        self._login_admin()
        existing = CasaDaMulherReport.objects.create(
            directorate=self.directorate,
            month=2,
            year=2031,
            user_id=self.admin_user.pk,
            created_by="alguem-antigo@example.com",
            cm_atend_mulheres_atendidas=1,
        )
        response = self.client.post(self.url, {
            "sub_id": str(existing.id),
            "key": "cm_atend_mulheres_atendidas",
            "value": "9",
            "month": "2",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.cm_atend_mulheres_atendidas, 9)
        self.assertEqual(existing.user_id, self.admin_user.pk)
        self.assertEqual(existing.created_by, self.admin_user.email)


class CasaMulherHomeViewSmokeTests(TestCase):
    """Smoke test basico da view principal (nao faz parte do diff, mas garante que
    o modulo ainda esta acessivel)."""

    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(email=self.admin_email, password=self.password)
        self.directorate = make_directorate()
        self.url = reverse("casamulher:home", kwargs={"pk": self.directorate.pk})

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_user_can_load_home(self):
        self.client.login(username=self.admin_email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

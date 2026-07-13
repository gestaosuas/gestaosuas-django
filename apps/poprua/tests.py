import uuid

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.directorates.models import Directorate

from .models import PopRuaReport


def make_user(email=None, password="senha12345", role=Profile.ROLE_ADMIN, full_name="Usuario Teste"):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(username=email, email=email, password=password)
    profile = Profile.objects.create(user=user, full_name=full_name, role=role)
    return user, profile


class PopRuaQuickEditViewTests(TestCase):
    """
    Cobre o comportamento alterado em PopRuaQuickEditView: get_or_create agora
    recebe defaults={"created_by": request.user} ao criar um relatorio novo —
    antes, um relatorio criado via quick-edit ficava com created_by nulo (a view
    nunca definia esse campo apos o get_or_create, diferente das outras QuickEditViews
    do projeto).

    A view resolve a diretoria internamente por
    Directorate.objects.filter(name__icontains="Populacao de Rua"), sem aceitar id
    explicito — por isso os testes usam a diretoria real ja existente no banco de
    dev, com ano/mes exclusivos para nao colidir com dados reais.
    """

    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(email=self.admin_email, password=self.password)
        self.directorate = Directorate.objects.filter(name__icontains="População de Rua").first()
        self.assertIsNotNone(
            self.directorate,
            "Diretoria 'População de Rua' não encontrada no banco de dev — pré-requisito do teste.",
        )
        self.url = reverse("poprua:quick_edit")

    def _login_admin(self):
        self.client.login(username=self.admin_email, password=self.password)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.post(self.url, {
            "key": "num_atend_centro_ref",
            "value": "4",
            "month": "1",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_user_forbidden(self):
        regular_email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        make_user(email=regular_email, password=self.password, role=Profile.ROLE_USER)
        self.client.login(username=regular_email, password=self.password)
        response = self.client.post(self.url, {
            "key": "num_atend_centro_ref",
            "value": "4",
            "month": "1",
            "year": "2031",
        })
        self.assertIn(response.status_code, (302, 403))

    def test_creates_new_report_sets_created_by_to_current_user(self):
        self._login_admin()
        response = self.client.post(self.url, {
            "key": "num_atend_centro_ref",
            "value": "4",
            "month": "1",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 200)
        report = PopRuaReport.objects.get(directorate=self.directorate, month=1, year=2031)
        self.assertEqual(report.num_atend_centro_ref, 4)
        self.assertEqual(str(report.created_by_id), str(self.admin_user.pk))

    def test_updating_existing_report_via_sub_id_does_not_touch_created_by(self):
        self._login_admin()
        other_user, _ = make_user()
        existing = PopRuaReport.objects.create(
            directorate=self.directorate,
            month=2,
            year=2031,
            created_by=other_user,
            num_atend_centro_ref=1,
        )
        response = self.client.post(self.url, {
            "sub_id": str(existing.id),
            "key": "num_atend_centro_ref",
            "value": "6",
            "month": "2",
            "year": "2031",
        })
        self.assertEqual(response.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.num_atend_centro_ref, 6)
        # get_or_create so aplica "defaults" na criacao; ao atualizar via sub_id o
        # created_by original permanece intocado.
        self.assertEqual(str(existing.created_by_id), str(other_user.pk))


class PopRuaDashboardViewSmokeTests(TestCase):
    """PopRua ainda esta em desenvolvimento; smoke test basico da view principal."""

    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(email=self.admin_email, password=self.password)
        self.url = reverse("poprua:dashboard")

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_user_can_load_dashboard(self):
        self.client.login(username=self.admin_email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

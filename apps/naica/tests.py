import uuid

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.directorates.models import Directorate

from .models import NaicaReport
from .views import NaicaQuickEditView


def make_user(email=None, password="senha12345", role=Profile.ROLE_ADMIN, full_name="Usuario Teste"):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(username=email, email=email, password=password)
    profile = Profile.objects.create(user=user, full_name=full_name, role=role)
    return user, profile


def get_existing_admin():
    """
    Retorna um Profile admin ja existente no banco de dev.

    Nao usamos um usuario recem-criado para os testes que gravam user_id: a coluna
    naica_reports.user_id ainda tem uma FK legada apontando para o schema Supabase
    residual `auth.users` (nao para accounts_user) neste banco de dev — confirmado
    via pg_constraint. Um uuid novo (uuid.uuid4() ou o id de um User Django recem
    criado) viola essa constraint com IntegrityError. Um admin ja migrado do
    Supabase satisfaz a FK porque seu id existe em auth.users.
    """
    return Profile.objects.filter(role=Profile.ROLE_ADMIN).select_related("user").first()


class NaicaQuickEditViewTests(TestCase):
    """
    Cobre o comportamento alterado em NaicaQuickEditView:
    - get_or_create agora recebe defaults={"user_id", "created_by"}.
    - Ao criar/atualizar sem user_id previo, o campo passa a receber o id do
      usuario autenticado (request.user.pk) em vez de um uuid.uuid4() aleatorio
      sem nenhuma relacao com o usuario (bug anterior).
    - created_by so e preenchido se ainda estiver vazio (nao sobrescreve valor existente).

    NOTA IMPORTANTE (bug real encontrado, nao corrigido — fora do escopo do
    diff testado): a URL nomeada "naica:quick-edit" (path "quick-edit/") fica
    "sombreada" pelo padrao `<dir_slug:pk>/`, declarado ANTES dela em
    apps/naica/urls.py — ambos casam com um unico segmento, e o primeiro
    padrao que bate vence. Um POST para /naica/quick-edit/ resolve para
    NaicaHomeView (kwargs={"pk": "quick-edit"}), que so aceita GET, retornando
    405 e nunca executando NaicaQuickEditView.post(). Confirmado com
    `resolve(reverse("naica:quick-edit"))`. Ou seja, o quick-edit do NAICA
    esta inacessivel via a URL nomeada em producao. Para nao deixar o
    comportamento alterado pelo diff sem cobertura por causa desse bug nao
    relacionado, os testes abaixo instanciam a view diretamente via
    RequestFactory, contornando o roteamento quebrado.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.admin_profile = get_existing_admin()
        self.assertIsNotNone(self.admin_profile, "Nenhum profile admin encontrado no banco de dev — pré-requisito do teste.")
        self.admin_user = self.admin_profile.user
        self.directorate = Directorate.objects.filter(name__icontains="NAICA").first()
        self.assertIsNotNone(self.directorate, "Diretoria NAICA não encontrada no banco de dev — pré-requisito do teste.")
        self.unit_name = f"UnidadeTeste{uuid.uuid4().hex[:6]}"

    def _post(self, data, user):
        request = self.factory.post("/naica/quick-edit/", data=data)
        request.user = user
        return NaicaQuickEditView.as_view()(request)

    def test_anonymous_user_redirected_to_login(self):
        response = self._post({
            "key": "total_atendidas",
            "value": "3",
            "month": "1",
            "year": "2031",
            "unit": self.unit_name,
        }, AnonymousUser())
        self.assertEqual(response.status_code, 302)

    def test_creates_new_report_sets_user_id_to_current_user_not_random(self):
        response = self._post({
            "key": "total_atendidas",
            "value": "3",
            "month": "1",
            "year": "2031",
            "unit": self.unit_name,
        }, self.admin_user)
        self.assertEqual(response.status_code, 200)
        report = NaicaReport.objects.get(directorate=self.directorate, unit_name=self.unit_name, month=1, year=2031)
        self.assertEqual(report.total_atendidas, 3)
        # Antes do fix, user_id recebia um uuid.uuid4() aleatorio sem relacao com o usuario.
        self.assertEqual(report.user_id, self.admin_user.pk)
        self.assertEqual(report.created_by, self.admin_user.email)

    def test_updating_existing_report_with_blank_created_by_gets_populated(self):
        # Nota: naica_reports.user_id declara null=True no model Django, mas a
        # coluna real no banco tem constraint NOT NULL (mais um caso de model
        # dessincronizado do schema real, ja que managed=False). Por isso usamos
        # um user_id valido aqui — so created_by comeca vazio nesta fixture.
        existing = NaicaReport.objects.create(
            directorate=self.directorate,
            unit_name=self.unit_name,
            month=2,
            year=2031,
            user_id=self.admin_user.pk,
            created_by="",
            total_atendidas=1,
        )
        response = self._post({
            "sub_id": str(existing.id),
            "key": "total_atendidas",
            "value": "8",
            "month": "2",
            "year": "2031",
            "unit": self.unit_name,
        }, self.admin_user)
        self.assertEqual(response.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.total_atendidas, 8)
        self.assertEqual(existing.user_id, self.admin_user.pk)
        self.assertEqual(existing.created_by, self.admin_user.email)

    def test_updating_existing_report_keeps_original_created_by_if_already_set(self):
        existing = NaicaReport.objects.create(
            directorate=self.directorate,
            unit_name=self.unit_name,
            month=3,
            year=2031,
            user_id=self.admin_user.pk,
            created_by="original@example.com",
            total_atendidas=1,
        )
        response = self._post({
            "sub_id": str(existing.id),
            "key": "total_atendidas",
            "value": "2",
            "month": "3",
            "year": "2031",
            "unit": self.unit_name,
        }, self.admin_user)
        self.assertEqual(response.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.total_atendidas, 2)
        # created_by so e preenchido se estava vazio — nao deve sobrescrever o valor existente.
        self.assertEqual(existing.created_by, "original@example.com")


class NaicaHomeViewSmokeTests(TestCase):
    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(email=self.admin_email, password=self.password)
        self.directorate = Directorate.objects.filter(name__icontains="NAICA").first()
        self.url = reverse("naica:home", kwargs={"pk": self.directorate.pk})

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_user_can_load_home(self):
        self.client.login(username=self.admin_email, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

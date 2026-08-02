import uuid

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, ProfileDirectorate, User
from apps.directorates.models import Directorate


def make_directorate(name=None):
    """Cria uma Directorate nova e única para uso em testes (tabela managed=False,
    id não tem default automático — precisa ser gerado manualmente)."""
    return Directorate.objects.create(
        id=uuid.uuid4(),
        name=name or f"Diretoria Teste {uuid.uuid4().hex[:8]}",
    )


def make_user(email=None, password="senha12345", role=Profile.ROLE_USER, full_name="Usuario Teste", **profile_kwargs):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(username=email, email=email, password=password)
    profile = Profile.objects.create(
        user=user,
        full_name=full_name,
        role=role,
        **profile_kwargs,
    )
    return user, profile


class LoginViewTests(TestCase):
    """Login por e-mail (username sincronizado com email)."""

    def setUp(self):
        self.email = f"login-{uuid.uuid4().hex[:8]}@example.com"
        self.password = "senha12345"
        self.user, self.profile = make_user(email=self.email, password=self.password)

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_email_and_password_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.email, "password": self.password},
        )
        # LoginView redireciona em caso de sucesso
        self.assertEqual(response.status_code, 302)
        # Confirma que a sessão está autenticada
        user_id = self.client.session.get("_auth_user_id")
        self.assertEqual(str(user_id), str(self.user.pk))

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.email, "password": "senha-errada"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get("_auth_user_id"))

    def test_login_redirect_authenticated_user(self):
        # redirect_authenticated_user=True: usuário já logado é redirecionado ao GET da página de login
        self.client.login(username=self.email, password=self.password)
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 302)


class LoginLockoutTests(TestCase):
    """LockoutModelBackend (apps/accounts/backends.py, 2026-07-29): trava
    login por username após MAX_ATTEMPTS falhas seguidas, mesmo se a senha
    certa vier depois; reseta o contador em qualquer sucesso."""

    def setUp(self):
        from django.core.cache import cache
        self.email = f"lockout-{uuid.uuid4().hex[:8]}@example.com"
        self.password = "senha12345"
        self.user, self.profile = make_user(email=self.email, password=self.password)
        self.addCleanup(cache.delete, f"login_attempts:{self.email.lower()}")

    def _attempt(self, password):
        return self.client.post(
            reverse("accounts:login"),
            {"username": self.email, "password": password},
        )

    def test_sixth_attempt_blocked_even_with_correct_password(self):
        from apps.accounts.backends import MAX_ATTEMPTS
        for _ in range(MAX_ATTEMPTS):
            self._attempt("senha-errada")
        response = self._attempt(self.password)
        self.assertIsNone(self.client.session.get("_auth_user_id"))
        self.assertEqual(response.status_code, 200)

    def test_successful_login_before_limit_resets_counter(self):
        for _ in range(2):
            self._attempt("senha-errada")
        response = self._attempt(self.password)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))

        self.client.logout()
        response = self._attempt(self.password)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))


class LogoutViewTests(TestCase):
    def setUp(self):
        self.email = f"logout-{uuid.uuid4().hex[:8]}@example.com"
        self.password = "senha12345"
        self.user, self.profile = make_user(email=self.email, password=self.password)

    def test_logout_clears_session(self):
        self.client.login(username=self.email, password=self.password)
        self.assertIsNotNone(self.client.session.get("_auth_user_id"))
        self.client.post(reverse("accounts:logout"))
        self.assertIsNone(self.client.session.get("_auth_user_id"))


class UserListViewPermissionTests(TestCase):
    """LoginRequiredMixin + AdminRequiredMixin em UserListView."""

    def setUp(self):
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.password = "senha12345"
        self.admin_user, self.admin_profile = make_user(
            email=self.admin_email, password=self.password, role=Profile.ROLE_ADMIN
        )

        self.regular_email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        self.regular_user, self.regular_profile = make_user(
            email=self.regular_email, password=self.password, role=Profile.ROLE_USER
        )

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_user_forbidden(self):
        self.client.login(username=self.regular_email, password=self.password)
        response = self.client.get(reverse("accounts:user_list"))
        # UserPassesTestMixin sem permissão -> 403 (raise_exception não configurado -> redireciona para login)
        self.assertIn(response.status_code, (302, 403))

    def test_admin_user_can_access_list(self):
        self.client.login(username=self.admin_email, password=self.password)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("profiles", response.context)

    def test_superuser_can_access_list_even_without_admin_profile_role(self):
        superuser_email = f"super-{uuid.uuid4().hex[:8]}@example.com"
        superuser = User.objects.create_superuser(
            username=superuser_email, email=superuser_email, password=self.password
        )
        Profile.objects.create(user=superuser, full_name="Super User", role=Profile.ROLE_USER)
        self.client.login(username=superuser_email, password=self.password)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)

    def test_search_filters_by_full_name(self):
        unique_name = f"NomeBuscavel{uuid.uuid4().hex[:6]}"
        make_user(full_name=unique_name)
        self.client.login(username=self.admin_email, password=self.password)
        response = self.client.get(reverse("accounts:user_list"), {"q": unique_name})
        self.assertEqual(response.status_code, 200)
        names = [p.full_name for p in response.context["profiles"]]
        self.assertIn(unique_name, names)
        self.assertNotIn(self.admin_profile.full_name, names)


class UserCreateViewTests(TestCase):
    """Cobre a view nova UserCreateView (criação de usuário + profile pelo admin)."""

    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(
            email=self.admin_email, password=self.password, role=Profile.ROLE_ADMIN
        )
        self.regular_email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        self.regular_user, self.regular_profile = make_user(
            email=self.regular_email, password=self.password, role=Profile.ROLE_USER
        )
        self.directorate = make_directorate()

    def _login_admin(self):
        self.client.login(username=self.admin_email, password=self.password)

    def test_anonymous_cannot_access_create_form(self):
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_cannot_access_create_form(self):
        self.client.login(username=self.regular_email, password=self.password)
        response = self.client.get(reverse("accounts:user_create"))
        self.assertIn(response.status_code, (302, 403))

    def test_admin_can_load_create_form(self):
        self._login_admin()
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("all_directorates", response.context)
        self.assertIn("role_choices", response.context)

    def test_admin_creates_user_successfully(self):
        self._login_admin()
        new_email = f"novo-{uuid.uuid4().hex[:8]}@example.com"
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Fulano de Tal",
                "email": new_email,
                "password": "senhaforte123",
                "role": Profile.ROLE_AGENTE,
                "primary_directorate": str(self.directorate.pk),
            },
        )
        created_user = User.objects.get(username=new_email)
        created_profile = Profile.objects.get(user=created_user)

        self.assertEqual(created_profile.full_name, "Fulano de Tal")
        self.assertEqual(created_profile.role, Profile.ROLE_AGENTE)
        self.assertEqual(created_profile.primary_directorate_id, self.directorate.pk)
        self.assertTrue(created_user.check_password("senhaforte123"))
        self.assertRedirects(
            response, reverse("accounts:user_permissions", kwargs={"pk": created_profile.pk})
        )

    def test_admin_creates_user_generates_unread_notification(self):
        """log_activity() adicionado em UserCreateView.post() (2026-07-29) —
        criação de usuário passa a aparecer no sino de notificações do admin."""
        self._login_admin()
        new_email = f"audit-{uuid.uuid4().hex[:8]}@example.com"
        self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Ciclana de Tal",
                "email": new_email,
                "password": "senhaforte123",
                "role": Profile.ROLE_AGENTE,
                "primary_directorate": str(self.directorate.pk),
            },
        )
        response = self.client.get(reverse("core:notifications-unread"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        messages_text = " ".join(item["message"] for item in data["items"])
        self.assertIn("Ciclana de Tal", messages_text)

    def test_create_user_missing_full_name_shows_error_and_does_not_create(self):
        self._login_admin()
        new_email = f"semnome-{uuid.uuid4().hex[:8]}@example.com"
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "",
                "email": new_email,
                "password": "senhaforte123",
                "role": Profile.ROLE_USER,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username=new_email).exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("Nome completo" in str(m) for m in messages))

    def test_create_user_short_password_rejected(self):
        self._login_admin()
        new_email = f"senhacurta-{uuid.uuid4().hex[:8]}@example.com"
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Nome Valido",
                "email": new_email,
                "password": "123",
                "role": Profile.ROLE_USER,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username=new_email).exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("8 caracteres" in str(m) for m in messages))

    def test_create_user_duplicate_email_rejected(self):
        self._login_admin()
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Outro Nome",
                "email": self.admin_email,  # já existe
                "password": "senhaforte123",
                "role": Profile.ROLE_USER,
            },
        )
        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(any("Já existe um usuário" in str(m) for m in messages))
        # Garante que nao duplicou o usuario existente
        self.assertEqual(User.objects.filter(username=self.admin_email).count(), 1)

    def test_create_user_invalid_role_rejected(self):
        self._login_admin()
        new_email = f"roleinvalido-{uuid.uuid4().hex[:8]}@example.com"
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Nome Valido",
                "email": new_email,
                "password": "senhaforte123",
                "role": "role-que-nao-existe",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username=new_email).exists())

    def test_create_user_without_primary_directorate_allowed(self):
        self._login_admin()
        new_email = f"semdiretoria-{uuid.uuid4().hex[:8]}@example.com"
        self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Sem Diretoria",
                "email": new_email,
                "password": "senhaforte123",
                "role": Profile.ROLE_USER,
                "primary_directorate": "",
            },
        )
        created_user = User.objects.get(username=new_email)
        created_profile = Profile.objects.get(user=created_user)
        self.assertIsNone(created_profile.primary_directorate_id)

    def test_create_user_email_is_lowercased(self):
        self._login_admin()
        mixed_case_email = f"MixedCase-{uuid.uuid4().hex[:8]}@Example.com"
        self.client.post(
            reverse("accounts:user_create"),
            {
                "full_name": "Case Test",
                "email": mixed_case_email,
                "password": "senhaforte123",
                "role": Profile.ROLE_USER,
            },
        )
        self.assertTrue(User.objects.filter(username=mixed_case_email.lower()).exists())


class UserPermissionsViewTests(TestCase):
    """Cobre UserPermissionsView, incluindo o comportamento novo de troca de
    e-mail/senha e o CRUD manual de ProfileDirectorate."""

    def setUp(self):
        self.password = "senha12345"
        self.admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        self.admin_user, self.admin_profile = make_user(
            email=self.admin_email, password=self.password, role=Profile.ROLE_ADMIN
        )
        self.regular_email = f"regular-{uuid.uuid4().hex[:8]}@example.com"
        self.regular_user, self.regular_profile = make_user(
            email=self.regular_email, password=self.password, role=Profile.ROLE_USER
        )

        self.target_email = f"target-{uuid.uuid4().hex[:8]}@example.com"
        self.target_user, self.target_profile = make_user(
            email=self.target_email, password=self.password, full_name="Alvo Original"
        )

        self.directorate_a = make_directorate()
        self.directorate_b = make_directorate()

    def _login_admin(self):
        self.client.login(username=self.admin_email, password=self.password)

    def _permissions_url(self, profile=None):
        profile = profile or self.target_profile
        return reverse("accounts:user_permissions", kwargs={"pk": profile.pk})

    def test_anonymous_cannot_access(self):
        response = self.client.get(self._permissions_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_cannot_access(self):
        self.client.login(username=self.regular_email, password=self.password)
        response = self.client.get(self._permissions_url())
        self.assertIn(response.status_code, (302, 403))

    def test_admin_can_load_permissions_form(self):
        self._login_admin()
        response = self.client.get(self._permissions_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("all_directorates", response.context)
        self.assertIn("current_links", response.context)

    def test_update_full_name_and_role(self):
        self._login_admin()
        response = self.client.post(
            self._permissions_url(),
            {
                "full_name": "Alvo Renomeado",
                "role": Profile.ROLE_DIRECTOR,
                "primary_directorate": "",
                "email": self.target_user.email,
            },
        )
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.full_name, "Alvo Renomeado")
        self.assertEqual(self.target_profile.role, Profile.ROLE_DIRECTOR)
        self.assertRedirects(response, reverse("accounts:user_list"))

    def test_change_email_updates_username_too(self):
        self._login_admin()
        new_email = f"novoemail-{uuid.uuid4().hex[:8]}@example.com"
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": new_email,
            },
        )
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.email, new_email)
        self.assertEqual(self.target_user.username, new_email)

    def test_change_email_to_existing_one_is_rejected(self):
        self._login_admin()
        response = self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.admin_email,  # já pertence a outro usuário
            },
            follow=True,
        )
        self.target_user.refresh_from_db()
        # e-mail não deve ter sido alterado
        self.assertEqual(self.target_user.email, self.target_email)
        messages_followed = list(response.context["messages"])
        self.assertTrue(any("Já existe outro usuário" in str(m) for m in messages_followed))
        # Regressão do bug corrigido em 2026-07: get_success_url() chamava
        # messages.success() incondicionalmente, mostrando um toast de sucesso
        # junto com o de erro. Agora só um dos dois deve aparecer.
        self.assertFalse(any("atualizadas!" in str(m) for m in messages_followed))

    def test_change_password_with_valid_length(self):
        self._login_admin()
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "new_password": "novasenha123",
            },
        )
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password("novasenha123"))

    def test_change_password_too_short_is_rejected(self):
        self._login_admin()
        old_password_hash = self.target_user.password
        response = self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "new_password": "123",
            },
            follow=True,
        )
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.password, old_password_hash)
        messages_followed = list(response.context["messages"])
        self.assertTrue(any("8 caracteres" in str(m) for m in messages_followed))
        self.assertFalse(any("atualizadas!" in str(m) for m in messages_followed))

    def test_blank_new_password_keeps_current_password(self):
        self._login_admin()
        old_password_hash = self.target_user.password
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "new_password": "",
            },
        )
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.password, old_password_hash)

    def test_assigning_directorates_creates_profile_directorate_links(self):
        self._login_admin()
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "directorates": [str(self.directorate_a.pk), str(self.directorate_b.pk)],
                f"units_{self.directorate_a.pk}": ["CRAS Teste"],
            },
        )
        links = ProfileDirectorate.objects.filter(profile=self.target_profile)
        self.assertEqual(links.count(), 2)
        link_a = links.get(directorate=self.directorate_a)
        self.assertEqual(link_a.allowed_units, ["CRAS Teste"])
        link_b = links.get(directorate=self.directorate_b)
        self.assertIsNone(link_b.allowed_units)

    def test_resubmitting_directorates_replaces_previous_links(self):
        self._login_admin()
        ProfileDirectorate.objects.create(
            profile=self.target_profile, directorate=self.directorate_a, allowed_units=None
        )
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "directorates": [str(self.directorate_b.pk)],
            },
        )
        links = ProfileDirectorate.objects.filter(profile=self.target_profile)
        self.assertEqual(links.count(), 1)
        self.assertEqual(links.first().directorate_id, self.directorate_b.pk)

    def test_comma_separated_units_fallback(self):
        self._login_admin()
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
                "directorates": [str(self.directorate_a.pk)],
                f"units_{self.directorate_a.pk}": "CRAS Um, CRAS Dois",
            },
        )
        link = ProfileDirectorate.objects.get(profile=self.target_profile, directorate=self.directorate_a)
        self.assertEqual(link.allowed_units, ["CRAS Um", "CRAS Dois"])

    def test_no_directorates_selected_clears_links(self):
        self._login_admin()
        ProfileDirectorate.objects.create(
            profile=self.target_profile, directorate=self.directorate_a, allowed_units=None
        )
        self.client.post(
            self._permissions_url(),
            {
                "full_name": self.target_profile.full_name,
                "role": self.target_profile.role,
                "primary_directorate": "",
                "email": self.target_user.email,
            },
        )
        self.assertFalse(ProfileDirectorate.objects.filter(profile=self.target_profile).exists())

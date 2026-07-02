from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_allowed_units(user, directorate):
    """
    Retorna as unidades que o usuário pode visualizar nesta diretoria.

    - None  → acesso total (admin ou sem restrição de unidade)
    - list  → lista de nomes de unidades permitidas (pode ser vazia = sem acesso)
    """
    from apps.accounts.models import ProfileDirectorate

    profile = getattr(user, "profile", None)

    if user.is_superuser or (profile and profile.role == "admin"):
        return None

    if not profile:
        return []

    # Diretoria primária → acesso total a todas as unidades
    if profile.primary_directorate_id and str(profile.primary_directorate_id) == str(directorate.pk):
        return None

    link = ProfileDirectorate.objects.filter(
        profile=profile,
        directorate_id=directorate.pk,
    ).first()

    if not link:
        return []

    if link.allowed_units is None:
        return None

    return link.allowed_units or []


def user_has_directorate_access(user, directorate):
    """Retorna True se o usuário tem algum acesso à diretoria."""
    from apps.accounts.models import ProfileDirectorate

    profile = getattr(user, "profile", None)
    if user.is_superuser or (profile and profile.role == "admin"):
        return True
    if not profile:
        return False
    if profile.primary_directorate_id and str(profile.primary_directorate_id) == str(directorate.pk):
        return True
    return ProfileDirectorate.objects.filter(
        profile=profile,
        directorate_id=directorate.pk,
    ).exists()


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class RoleRequiredMixin(AccessMixin):
    """Verifica se o usuário possui um dos papéis permitidos."""
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, "profile", None)
        user_role = profile.role if profile else "user"
        if user_role not in self.allowed_roles and not request.user.is_superuser:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class DirectorateAccessMixin(LoginRequiredMixin):
    """
    Mixin base para todos os módulos (CRAS, NAICA, etc.).
    Bloqueia acesso se o usuário não tiver vínculo com a diretoria.
    Disponibiliza: get_allowed_units(), filter_units(), is_admin(), is_diretor().
    """

    def get_directorate(self):
        raise NotImplementedError("Implemente get_directorate() na subclasse.")

    # --- Helpers de papel ---

    def is_admin(self):
        profile = getattr(self.request.user, "profile", None)
        return self.request.user.is_superuser or (profile and profile.role == "admin")

    def is_diretor(self):
        profile = getattr(self.request.user, "profile", None)
        return bool(profile and profile.role == "diretor")

    def is_agente(self):
        return not self.is_admin() and not self.is_diretor()

    # --- Unidades permitidas ---

    def get_allowed_units(self):
        """None = todas as unidades; list = apenas essas."""
        try:
            directorate = self.get_directorate()
        except Exception:
            return []
        return get_user_allowed_units(self.request.user, directorate)

    def filter_units(self, all_units):
        """Filtra lista de unidades baseado nas permissões."""
        allowed = self.get_allowed_units()
        if allowed is None:
            return list(all_units)
        return [u for u in all_units if u in allowed]

    # --- Controle de acesso ---

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        profile = getattr(request.user, "profile", None)

        if request.user.is_superuser or (profile and profile.role == "admin"):
            return super().dispatch(request, *args, **kwargs)

        try:
            directorate = self.get_directorate()
        except Exception:
            messages.error(request, "Diretoria não encontrada.")
            return redirect("core:landing")

        if not user_has_directorate_access(request.user, directorate):
            messages.error(request, "Você não tem acesso a esta área.")
            return redirect("core:landing")

        return super().dispatch(request, *args, **kwargs)

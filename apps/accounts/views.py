from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, UpdateView, View
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from .models import Profile, ProfileDirectorate, User
from apps.directorates.models import Directorate


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or 
            (hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin')
        )


class UserListView(AdminRequiredMixin, ListView):
    model = Profile
    template_name = "accounts/user_list.html"
    context_object_name = "profiles"
    paginate_by = 20

    def get_queryset(self):
        queryset = Profile.objects.select_related('primary_directorate', 'user').all()
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        return queryset


class UserCreateView(AdminRequiredMixin, View):
    template_name = "accounts/user_create.html"

    def get_context(self, form_data=None):
        return {
            "all_directorates": Directorate.objects.all().order_by("name"),
            "role_choices": Profile.ROLE_CHOICES,
            "form_data": form_data or {},
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context())

    def post(self, request, *args, **kwargs):
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        role = request.POST.get("role") or Profile.ROLE_USER
        primary_directorate_id = request.POST.get("primary_directorate") or None

        errors = []
        if not full_name:
            errors.append("Nome completo é obrigatório.")
        if not email:
            errors.append("E-mail é obrigatório.")
        elif User.objects.filter(username=email).exists():
            errors.append("Já existe um usuário cadastrado com este e-mail.")
        if len(password) < 8:
            errors.append("A senha deve ter pelo menos 8 caracteres.")
        if role not in dict(Profile.ROLE_CHOICES):
            errors.append("Nível de acesso inválido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, self.template_name, self.get_context(form_data=request.POST))

        user = User.objects.create_user(username=email, email=email, password=password)
        profile = Profile.objects.create(
            user=user,
            full_name=full_name,
            role=role,
            primary_directorate_id=primary_directorate_id,
            created_at=timezone.now(),
        )
        messages.success(request, f"Usuário {full_name} criado com sucesso!")
        return redirect("accounts:user_permissions", pk=profile.pk)


class UserPermissionsView(AdminRequiredMixin, UpdateView):
    model = Profile
    template_name = "accounts/user_permissions.html"
    fields = ['full_name', 'role', 'primary_directorate']
    
    def get_success_url(self):
        return reverse_lazy('accounts:user_list')

    def get_unit_options_map(self, directorates):
        """Unidades/sub-áreas marcáveis por diretoria, quando existir o conceito.
        Ausência de entrada aqui = diretoria é só liga/desliga (sem unidade) —
        ver docs/dominio/03 e CLAUDE.md sobre managed=False/schema por diretoria."""
        from apps.core.utils import strip_accents

        unit_options = {}
        for d in directorates:
            name = strip_accents(d.name.lower())
            if 'cras' in name:
                from apps.cras.views import CRAS_UNITS
                unit_options[str(d.pk)] = CRAS_UNITS
            elif 'naica' in name:
                from apps.naica.views import NAICA_UNITS
                unit_options[str(d.pk)] = NAICA_UNITS
            elif 'ceai' in name:
                from apps.ceai.constants import CEAI_UNITS
                unit_options[str(d.pk)] = CEAI_UNITS
            elif 'protecao especial' in name:
                unit_options[str(d.pk)] = ["Creas Protetivo", "Creas Socioeducativo"]
            elif 'sine' in name or 'qual' in name or 'profissional' in name:
                unit_options[str(d.pk)] = ["Centro Profissionalizante", "SINE"]
        return unit_options

    def get_context_data(self, **kwargs):
        from apps.core.utils import strip_accents

        context = super().get_context_data(**kwargs)
        directorates = Directorate.objects.all().order_by('name')
        context['all_directorates'] = directorates
        context['unit_options_map'] = self.get_unit_options_map(directorates)

        # Agrupa Subvenção/Emendas e Fundos/Outros num único card visual "Monitoramento"
        # (pedido do usuário) — continuam sendo 3 vínculos independentes.
        monitoramento_directorates = []
        other_directorates = []
        for d in directorates:
            name = strip_accents(d.name.strip().lower())
            if name in ('outros',) or 'subvencao' in name or 'emendas' in name or 'fundos' in name:
                monitoramento_directorates.append(d)
            else:
                other_directorates.append(d)
        context['monitoramento_directorates'] = monitoramento_directorates
        context['other_directorates'] = other_directorates

        # Get current links and their allowed_units
        current_links = {
            link['directorate_id']: link['allowed_units'] 
            for link in ProfileDirectorate.objects.filter(profile=self.object).values('directorate_id', 'allowed_units')
        }
        context['current_links'] = current_links
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            profile = form.save()
            has_error = False

            # Handle email change (username is kept in sync with e-mail for login)
            new_email = request.POST.get("email", "").strip().lower()
            if new_email and new_email != profile.user.email:
                if User.objects.exclude(pk=profile.user.pk).filter(username=new_email).exists():
                    messages.error(request, "Já existe outro usuário com este e-mail. O e-mail não foi alterado.")
                    has_error = True
                else:
                    profile.user.email = new_email
                    profile.user.username = new_email
                    profile.user.save(update_fields=["email", "username"])

            # Handle password change (optional — blank keeps current password)
            new_password = request.POST.get("new_password", "").strip()
            if new_password:
                if len(new_password) < 8:
                    messages.error(request, "A senha deve ter pelo menos 8 caracteres. As demais alterações foram salvas.")
                    has_error = True
                else:
                    profile.user.set_password(new_password)
                    profile.user.save(update_fields=["password"])

            # Handle profile_directorates (additional access)
            selected_directorates = request.POST.getlist('directorates')
            unit_options_map = self.get_unit_options_map(
                Directorate.objects.filter(pk__in=selected_directorates)
            )

            # We are using managed=False, but Django can still do basic CRUD
            # if the table structure matches.
            # However, for profile_directorates, it's safer to use manual logic
            # if we want to update allowed_units per directorate.

            # 1. Clear existing links (or update them)
            ProfileDirectorate.objects.filter(profile=profile).delete()

            # 2. Add new links
            for dir_id in selected_directorates:
                checked_units = [u.strip() for u in request.POST.getlist(f'units_{dir_id}') if u.strip()]

                if dir_id not in unit_options_map:
                    # Diretoria sem conceito de unidade (ex.: Benefícios, Casa da
                    # Mulher): marcar a diretoria já dá acesso total, sem lista.
                    allowed_units = None
                elif profile.role == Profile.ROLE_DIRECTOR:
                    # Diretor sempre enxerga/envia para todas as unidades da
                    # diretoria, mesmo sem marcar nenhuma individualmente.
                    allowed_units = None
                else:
                    # Agente: só as unidades marcadas. Lista vazia fica vazia de
                    # propósito (== nenhum acesso ainda) — antes isso virava
                    # None (acesso total) por engano.
                    allowed_units = checked_units

                ProfileDirectorate.objects.create(
                    profile=profile,
                    directorate_id=dir_id,
                    allowed_units=allowed_units
                )

            if not has_error:
                messages.success(request, f"Permissões de {profile.full_name} atualizadas!")
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Profile, ProfileDirectorate
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
        queryset = Profile.objects.select_related('primary_directorate').all()
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        return queryset


class UserPermissionsView(AdminRequiredMixin, UpdateView):
    model = Profile
    template_name = "accounts/user_permissions.html"
    fields = ['full_name', 'role', 'primary_directorate']
    
    def get_success_url(self):
        messages.success(self.request, f"Permissões de {self.object.full_name} atualizadas!")
        return reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorates = Directorate.objects.all().order_by('name')
        context['all_directorates'] = directorates
        
        # Unit options for each directorate type
        unit_options = {}
        for d in directorates:
            name = d.name.lower()
            if 'cras' in name:
                from apps.cras.views import CRAS_UNITS
                unit_options[str(d.pk)] = CRAS_UNITS
            elif 'sine' in name or 'qual' in name or 'profissional' in name:
                unit_options[str(d.pk)] = ["Centro Profissionalizante", "SINE"]
        
        context['unit_options_map'] = unit_options
        
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
            
            # Handle profile_directorates (additional access)
            selected_directorates = request.POST.getlist('directorates')
            
            # We are using managed=False, but Django can still do basic CRUD 
            # if the table structure matches. 
            # However, for profile_directorates, it's safer to use manual logic 
            # if we want to update allowed_units per directorate.
            
            # 1. Clear existing links (or update them)
            ProfileDirectorate.objects.filter(profile=profile).delete()
            
            # 2. Add new links
            for dir_id in selected_directorates:
                units_data = request.POST.getlist(f'units_{dir_id}')
                
                # If it's a single item with a comma, it might be from the text input fallback
                if len(units_data) == 1 and ',' in units_data[0]:
                    allowed_units = [u.strip() for u in units_data[0].split(',') if u.strip()]
                else:
                    allowed_units = [u.strip() for u in units_data if u.strip()]
                
                if not allowed_units:
                    allowed_units = None
                
                ProfileDirectorate.objects.create(
                    profile=profile,
                    directorate_id=dir_id,
                    allowed_units=allowed_units
                )
            
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

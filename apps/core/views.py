import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError, ProgrammingError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, RedirectView, View

from apps.accounts.mixins import RoleRequiredMixin
from apps.accounts.models import Profile
from apps.directorates.models import Directorate


class LandingView(RedirectView):
    url = "/mapas/"


class SystemSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "core/settings.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from apps.core.models import SystemSetting
            settings = {item.key: item.value for item in SystemSetting.objects.all()}
        except:
            settings = {}
        context["system_name"] = settings.get("system_name", "Plataforma de Vigilancia Socioassistencial")
        context["logo_url"] = settings.get("logo_url", "")
        return context
    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from apps.core.models import SystemSetting
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return redirect('core:home')
        sn = request.POST.get("system_name")
        lu = request.POST.get("logo_url")
        SystemSetting.objects.update_or_create(key="system_name", defaults={"value": sn})
        SystemSetting.objects.update_or_create(key="logo_url", defaults={"value": lu})
        messages.success(request, "Configurações salvas.")
        return redirect("core:settings")


def _tv_build_urls():
    """Build list of [url, label] for all TV-eligible directorates."""
    from datetime import date
    year = date.today().year
    urls = []
    idx = 0
    for d in Directorate.objects.order_by("name"):
        n = d.name.lower()
        pk = str(d.pk)
        if "sine" in n or "qual" in n or "profissional" in n:
            urls.append([f"/sine-cp/painel/?tab=sine&year={year}&tv=1&slide={idx}", f"SINE — {d.name}"]); idx += 1
            urls.append([f"/sine-cp/painel/?tab=cp&year={year}&tv=1&slide={idx}", f"Qualificação — {d.name}"]); idx += 1
        elif "benef" in n:
            urls.append([f"/beneficios/painel/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "cras" in n and "creas" not in n:
            urls.append([f"/cras/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "creas" in n:
            urls.append([f"/creasidoso/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "naica" in n:
            urls.append([f"/naica/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "ceai" in n:
            urls.append([f"/ceai/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "pop" in n or "rua" in n:
            urls.append([f"/poprua/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "prote" in n:
            # "prote" (nao "protec") de proposito - "Proteção Especial" no
            # banco vem com encoding corrompido ("Prote��o"), entao
            # "protec" nunca batia e essa diretoria sumia do carrossel
            # silenciosamente (bug pre-existente, achado e corrigido aqui).
            urls.append([f"/protecao-especial/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "casa" in n or "mulher" in n:
            urls.append([f"/casa-mulher/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "subven" in n or "emenda" in n or "fundo" in n or n.strip() == "outros":
            urls.append([f"/monitoramento/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
    # Add total to all URLs
    total = len(urls)
    for u in urls:
        u[0] += f"&total={total}"
    return urls


class TvDashboardView(LoginRequiredMixin, RedirectView):
    """Redirect to the first TV slide."""

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            if profile.role != "admin":
                raise Http404
        except (Profile.DoesNotExist, OperationalError, ProgrammingError):
            raise Http404
        slides = _tv_build_urls()
        if not slides:
            return "/mapas/"
        urls_json = __import__("json").dumps(slides)
        self.request.session["tv_urls"] = __import__("json").dumps(slides)
        return slides[0][0]


class TvApiUrlsView(LoginRequiredMixin, View):
    """JSON endpoint returning all TV slide URLs."""

    def get(self, request):
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
            if profile.role != "admin":
                return JsonResponse({"error": "forbidden"}, status=403)
        except (Profile.DoesNotExist, OperationalError, ProgrammingError):
            return JsonResponse({"error": "forbidden"}, status=403)
        slides = _tv_build_urls()
        return JsonResponse({"slides": slides, "total": len(slides)})


class NotificationsUnreadView(LoginRequiredMixin, View):
    """JSON endpoint returning unread activity-log notifications (admin only)."""

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role != "admin":
                return JsonResponse({"error": "forbidden"}, status=403)
        except (Profile.DoesNotExist, OperationalError, ProgrammingError):
            return JsonResponse({"error": "forbidden"}, status=403)

        from apps.core.models import ActivityLog
        from apps.core.notifications import ACTION_VERBS

        items = []
        for log in ActivityLog.objects.filter(read_at__isnull=True).order_by("-created_at")[:30]:
            verb = ACTION_VERBS.get(log.action_type, log.action_type)
            items.append({
                "id": str(log.id),
                "message": f"{log.user_name} {verb} {log.resource_name}",
                "directorate_name": log.directorate_name,
                "url": (log.details or {}).get("url", ""),
                "created_at": log.created_at.isoformat() if log.created_at else "",
            })
        return JsonResponse({"count": len(items), "items": items})


class NotificationsMarkReadView(LoginRequiredMixin, View):
    """Marks all currently-unread notifications as read (admin only)."""

    def post(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role != "admin":
                return JsonResponse({"error": "forbidden"}, status=403)
        except (Profile.DoesNotExist, OperationalError, ProgrammingError):
            return JsonResponse({"error": "forbidden"}, status=403)

        from django.utils import timezone
        from apps.core.models import ActivityLog

        ActivityLog.objects.filter(read_at__isnull=True).update(read_at=timezone.now())
        return JsonResponse({"status": "success"})


class NotificationsListView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Página com o histórico completo do sininho, agrupado por dia (não só
    as não lidas — o dropdown do sininho mostra só as pendentes)."""
    template_name = "core/notifications.html"
    allowed_roles = ["admin"]

    def get_context_data(self, **kwargs):
        from itertools import groupby
        from datetime import timedelta
        from django.utils import timezone
        from apps.core.models import ActivityLog
        from apps.core.notifications import ACTION_VERBS

        context = super().get_context_data(**kwargs)
        window_days = 30
        cutoff = timezone.now() - timedelta(days=window_days)
        logs = ActivityLog.objects.filter(created_at__gte=cutoff).order_by("-created_at")

        today = timezone.localtime(timezone.now()).date()
        yesterday = today - timedelta(days=1)
        month_names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                       "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

        days = []
        for day, entries in groupby(logs, key=lambda log: timezone.localtime(log.created_at).date()):
            if day == today:
                label = "Hoje"
            elif day == yesterday:
                label = "Ontem"
            else:
                label = f"{day.day} de {month_names[day.month - 1]} de {day.year}"

            items = []
            for log in entries:
                verb = ACTION_VERBS.get(log.action_type, log.action_type)
                items.append({
                    "message": f"{log.user_name} {verb} {log.resource_name}",
                    "directorate_name": log.directorate_name,
                    "url": (log.details or {}).get("url", ""),
                    "time": timezone.localtime(log.created_at).strftime("%H:%M"),
                })
            days.append({"date": day, "label": label, "items": items})

        context["days"] = days
        context["window_days"] = window_days
        return context


class ProtectedMediaView(LoginRequiredMixin, View):
    """Serve arquivos de MEDIA_ROOT só para usuários autenticados.

    Substitui o link cru pra /media/ (só registrado com DEBUG=True em
    config/urls.py — 404 em produção) por uma rota que funciona em prod e
    exige login. Valida que o caminho resolvido continua dentro de
    MEDIA_ROOT antes de servir, contra path traversal (../, caminho
    absoluto etc.).
    """

    def get(self, request, file_path):
        media_root = os.path.realpath(str(settings.MEDIA_ROOT))
        full_path = os.path.realpath(os.path.join(media_root, file_path))
        if full_path != media_root and not full_path.startswith(media_root + os.sep):
            raise Http404
        if not os.path.isfile(full_path):
            raise Http404
        return FileResponse(open(full_path, "rb"))


class MapView(LoginRequiredMixin, TemplateView):
    template_name = "core/map.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import MapUnit, MapCategory
        context["categories"] = list(MapCategory.objects.all().order_by("name"))
        context["map_units"] = list(MapUnit.objects.select_related("category").all().order_by("name"))
        return context


class MapManagementView(LoginRequiredMixin, TemplateView):
    template_name = "core/map_management.html"
    def get(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return redirect('core:map')
        return super().get(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import MapUnit, MapCategory
        context["categories"] = list(MapCategory.objects.all().order_by("name"))
        context["map_units"] = list(MapUnit.objects.select_related("category").all().order_by("name"))
        return context
    def post(self, request, *args, **kwargs):
        from apps.core.models import MapUnit, MapCategory
        from django.shortcuts import redirect
        from django.contrib import messages
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return redirect('core:map')
        action = request.POST.get("action")
        if action == "save_category":
            cat_id = request.POST.get("category_id")
            name = request.POST.get("name")
            color = request.POST.get("color")
            if cat_id:
                MapCategory.objects.filter(id=cat_id).update(name=name, color=color)
                messages.success(request, "Categoria atualizada.")
            else:
                MapCategory.objects.create(name=name, color=color)
                messages.success(request, "Categoria criada.")
        elif action == "delete_category":
            cat_id = request.POST.get("category_id")
            if cat_id:
                MapCategory.objects.filter(id=cat_id).delete()
                messages.success(request, "Categoria removida.")
        elif action == "save_unit":
            unit_id = request.POST.get("unit_id")
            name = request.POST.get("name")
            category_id = request.POST.get("category")
            region = request.POST.get("region")
            address = request.POST.get("address")
            phone = request.POST.get("phone")
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")
            def to_dec(val):
                if not val: return None
                try:
                    from decimal import Decimal
                    return Decimal(str(val).replace(",", "."))
                except: return None
            defaults = {"name": name, "category_id": category_id if category_id else None,
                        "region": region, "address": address, "phone": phone,
                        "latitude": to_dec(latitude), "longitude": to_dec(longitude)}
            if unit_id:
                MapUnit.objects.filter(id=unit_id).update(**defaults)
                messages.success(request, "Unidade atualizada.")
            else:
                MapUnit.objects.create(**defaults)
                messages.success(request, "Unidade criada.")
        elif action == "delete_unit":
            unit_id = request.POST.get("unit_id")
            if unit_id:
                MapUnit.objects.filter(id=unit_id).delete()
                messages.success(request, "Unidade removida.")
        return redirect("core:map_management")


class NarrativeReportDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Exclui um MonthlyReport (Relatorio Mensal narrativo) de qualquer
    diretoria/setor -- endpoint unico reaproveitado pelo sidebar de
    historico de todas as diretorias (ver templates/directorates/shared/
    narrative_report.html). Admin-only: mesma regra de "só admin edita/
    exclui relatório já finalizado" pedida pelo usuário para o botão de
    editar.
    """
    allowed_roles = ["admin"]

    def post(self, request, *args, **kwargs):
        from apps.directorates.models import MonthlyReport

        report_id = request.POST.get("report_id")
        MonthlyReport.objects.filter(pk=report_id).delete()
        messages.success(request, "Relatório excluído.")

        next_url = request.POST.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect(reverse("core:map"))

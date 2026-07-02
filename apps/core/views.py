from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError, ProgrammingError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView, RedirectView, View

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
        from apps.core.models import SystemSetting, messages
        sn = request.POST.get("system_name")
        lu = request.POST.get("logo_url")
        SystemSetting.objects.update_or_create(key="system_name", defaults={"value": sn})
        SystemSetting.objects.update_or_create(key="logo_url", defaults={"value": lu})
        messages.success(request, "Configurações salvas.")
        return redirect("core:settings")


EXCLUDE_NAMES = ["Subvenção", "Subvencao", "Emendas", "Outros"]

def _tv_build_urls():
    """Build list of [url, label] for all TV-eligible directorates."""
    from datetime import date
    year = date.today().year
    urls = []
    idx = 0
    for d in Directorate.objects.order_by("name"):
        n = d.name.lower()
        pk = str(d.pk)
        if any(e in n for e in EXCLUDE_NAMES):
            continue
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
        elif "protec" in n:
            urls.append([f"/protecao-especial/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
        elif "casa" in n or "mulher" in n:
            urls.append([f"/casa-mulher/{pk}/?year={year}&tv=1&slide={idx}", d.name]); idx += 1
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

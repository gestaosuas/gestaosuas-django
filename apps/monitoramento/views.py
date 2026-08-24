import uuid
import math
import unicodedata
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View

from apps.accounts.mixins import DirectorateAccessMixin, RoleRequiredMixin
from apps.accounts.models import Profile, ProfileDirectorate
from apps.core.export import ExcelExportMixin, build_workbook
from apps.core.notifications import log_activity
from apps.directorates.models import Directorate, FormDelegation, MonthlyReport, Osc, Visit, WorkPlan
from apps.directorates.forms import OscForm
from apps.directorates.views import (
    build_delegation_map,
    build_registered_by_map,
    get_admin_user_ids,
    get_monitoramento_theme,
    is_subvencao_directorate,
)
from apps.core.utils import (
    MONTH_LABELS, MONTH_OPTIONS, build_sparkline,
    build_period_label, build_year_range_from_years, build_variation
)
from .models import GenericMonitoringReport
from .forms import GenericMonitoringForm
import json

BIMESTER_LABELS = ["Jan/Fev", "Mar/Abr", "Mai/Jun", "Jul/Ago", "Set/Out", "Nov/Dez"]
BIMESTER_OPTIONS = [(i + 1, f"{i+1}o Bimestre ({BIMESTER_LABELS[i]})") for i in range(6)]

def current_bimester():
    return math.ceil(datetime.now().month / 2)

def bimester_months(bimester):
    return (bimester - 1) * 2 + 1, bimester * 2

def get_persistent_bimester(request):
    bimester = request.GET.get("bimestre")
    if bimester is not None:
        request.session["selected_bimester"] = bimester
    else:
        bimester = request.session.get("selected_bimester", str(current_bimester()))
    return bimester



def strip_accents(text):
    return "".join(
        char for char in unicodedata.normalize("NFD", text or "")
        if unicodedata.category(char) != "Mn"
    )


def title_name(value):
    return " ".join(part.capitalize() for part in str(value or "").split())


class MonitoramentoBaseMixin(DirectorateAccessMixin):
    def get_directorate(self):
        directorate = Directorate.objects.filter(pk=self.kwargs["pk"]).first()
        if not directorate:
            raise Http404("Diretoria nao encontrada.")
        return directorate

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"

    def get_reference(self):
        ref = self.request.GET.get("ref")
        if not ref:
            directorate = self.get_directorate()
            ref = directorate.name.lower().replace(" ", "_")
        return ref


class MonitoramentoHomeView(MonitoramentoBaseMixin, DetailView):
    template_name = "monitoramento/home.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_template_names(self):
        # Troca de aba via JS busca só o fragmento (ver tabContentRegion em
        # home.html) em vez da página inteira - evita recarregar navbar/
        # cabecalho/cards a cada clique. Fallback (sem X-Requested-With,
        # ex. acesso direto por URL/bookmark) sempre renderiza a pagina cheia.
        # ?tv=1 (carrossel de TV) tem prioridade sobre os dois - nao dá pra só
        # usar TvTemplateMixin aqui porque esse metodo já é sobrescrito nesta
        # classe (um metodo definido direto na classe sempre vence o mixin).
        if self.request.GET.get("tv") == "1":
            return ["monitoramento/tv.html"]
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return ["monitoramento/_tab_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.object
        selected_year = self.get_year()
        selected_month = self.get_month()
        bimester = get_persistent_bimester(self.request)
        reference = self.get_reference()

        context["selected_year"] = int(selected_year)
        context["selected_month"] = selected_month
        context["selected_bimester"] = bimester
        context["months_range"] = MONTH_OPTIONS
        context["years_range"] = build_year_range_from_years([], selected_year)
        context["bimester_options"] = BIMESTER_OPTIONS
        context["bimester_label"] = ""

        profile = getattr(self.request.user, "profile", None)
        is_admin = self.request.user.is_superuser or (profile and profile.role == "admin")
        context["is_admin_user"] = is_admin

        # Bimester calculation
        curr_year = int(selected_year)
        if bimester != "all":
            curr_bimester = int(bimester)
            b_start, b_end = bimester_months(curr_bimester)
            context["bimester_label"] = f"{curr_bimester}o Bimestre ({BIMESTER_LABELS[curr_bimester-1]})"

            visits_qs = directorate.visits.filter(
                visit_date__year=curr_year,
                visit_date__month__gte=b_start,
                visit_date__month__lte=b_end,
            )
        else:
            visits_qs = directorate.visits.filter(visit_date__year=curr_year)

        stats_visits = list(visits_qs)
        dashboard_visits_qs = visits_qs.select_related("osc", "directorate", "work_plan").order_by("-visit_date", "-created_at")
        if not is_admin:
            if profile and profile.role == "diretor":
                is_primary = str(profile.primary_directorate_id) == str(directorate.pk)
                is_linked = ProfileDirectorate.objects.filter(profile=profile, directorate=directorate).exists()
                if not (is_primary or is_linked):
                    dashboard_visits_qs = dashboard_visits_qs.none()
                else:
                    dashboard_visits_qs = dashboard_visits_qs.exclude(user_id__in=get_admin_user_ids())
            else:
                # Mesma regra de VisitListView/MonitoringReportListView: em
                # Subvencao/Emendas e Fundos, agente ve as visitas de outros
                # agentes da mesma diretoria tambem (2026-08-19), mas visita
                # delegada continua visivel mesmo se admin-criada (fix
                # 2026-08-20 - ver apps/directorates/views.py VisitListView
                # pro detalhe do bug: a exclusao de admin escondia o caso
                # mais comum de delegacao, admin cria e delega pra agente).
                delegated_visit_ids = FormDelegation.objects.filter(user_id=self.request.user.id).values_list("visit_id", flat=True)
                if is_subvencao_directorate(directorate):
                    dashboard_visits_qs = dashboard_visits_qs.filter(Q(id__in=delegated_visit_ids) | ~Q(user_id__in=get_admin_user_ids()))
                else:
                    dashboard_visits_qs = dashboard_visits_qs.filter(Q(user_id=self.request.user.id) | Q(id__in=delegated_visit_ids))

        all_visits = list(dashboard_visits_qs)
        registered_by_map = build_registered_by_map(all_visits)
        delegation_map = build_delegation_map(all_visits)
        for visit in all_visits:
            identificacao = visit.identificacao or {}
            visit.registered_by_name = (
                identificacao.get("registered_by_name")
                or identificacao.get("registrado_por")
                or registered_by_map.get(visit.user_id)
                or "Desconhecido"
            )
            assinaturas = visit.assinaturas or {}
            visit.tecnico1_display = title_name(assinaturas.get("tecnico1_nome", ""))
            visit.tecnico2_display = title_name(assinaturas.get("tecnico2_nome", ""))
            relatorio = visit.parecer_tecnico or {}
            visit.relatorio_status = relatorio.get("status") if isinstance(relatorio, dict) else None
            visit.delegated_user_ids_str = ",".join(str(uid) for uid in delegation_map.get(visit.pk, []))
            visit.is_delegated = bool(delegation_map.get(visit.pk))

        _total_visits = len(stats_visits)
        _finalized_visits = len([v for v in stats_visits if v.status in ["completed", "finalized"]])
        _draft_visits = len([v for v in stats_visits if v.status == "draft"])
        _finalization_rate = int(_finalized_visits / _total_visits * 100) if _total_visits else 0
        subvencao_stats = {
            "totalOSCs": directorate.oscs.count(),
            "totalVisits": _total_visits,
            "finalizedVisits": _finalized_visits,
            "draftVisits": _draft_visits,
            "finalizationRate": _finalization_rate,
        }

        # Visitas por mes no ano selecionado (independente do filtro de bimestre)
        # para o grafico da tela inicial do dashboard.
        year_visit_dates = directorate.visits.filter(visit_date__year=curr_year).values_list("visit_date", flat=True)
        visits_by_month = [0] * 12
        for visit_date in year_visit_dates:
            if visit_date:
                visits_by_month[visit_date.month - 1] += 1
        context["visits_by_month_labels_json"] = json.dumps([label.title() for _num, label in MONTH_LABELS])
        context["visits_by_month_data_json"] = json.dumps(visits_by_month)

        # "Visitas" (donut) e "Relatorios de Visita" (barras) - mesmo escopo
        # (bimestre/ano selecionados) dos demais cards da tela inicial.
        context["visits_donut_data_json"] = json.dumps([_finalized_visits, _draft_visits])

        _report_finalized = len([v for v in stats_visits if (v.relatorio_final or {}).get("status") == "finalized"])
        _report_draft = max(_total_visits - _report_finalized, 0)
        context["reports_bar_data_json"] = json.dumps([_report_finalized, _report_draft])

        # Theme detection
        normalized = directorate.name.lower()
        ascii_name = strip_accents(normalized)
        is_subvencao = "subvencao" in ascii_name or "emendas" in ascii_name or "fundos" in ascii_name
        is_subvencao_only = is_subvencao
        is_outros = "outros" in normalized

        # Diretor/agente so enxergam as abas "Instrumental de Visita" e
        # "Relatorios e Pareceres" (nenhuma delas em Outros, que nao tem essa
        # aba) - "Cadastrar OSC", "Plano de Trabalho" e a tela "overview" de
        # KPIs ficam so pro admin (docs/dominio/04-... A.6, confirmado
        # 2026-07-25). Allowlist, nao blocklist: qualquer ?tab= fora do
        # permitido (incluindo o default "overview") cai em "visits".
        allowed_tabs = {"visits"} if is_outros else {"visits", "reports"}
        requested_tab = self.request.GET.get("tab", "overview" if is_admin else "visits")
        if not is_admin and requested_tab not in allowed_tabs:
            requested_tab = "visits"
        context["dashboard_tab"] = requested_tab

        theme_class, header_class, icon_color = get_monitoramento_theme(directorate)

        is_emendas_flag = "emendas" in ascii_name

        context.update({
            "subvencao_stats": subvencao_stats,
            "is_subvencao_only": is_subvencao_only,
            "is_emendas": is_emendas_flag,
            "is_fundos": "fundos" in ascii_name,
            "is_subvencao_mode": is_subvencao and not is_outros,
            "is_outros_mode": is_outros,
            # "Outros" usa o mesmo dashboard com abas de Subvencao/Emendas e Fundos,
            # mas so com 2 das 4 abas (ver home.html/_tab_content.html) - sem Plano
            # de Trabalho nem Relatorios e Pareceres.
            "show_visit_tabs": is_subvencao_only or is_outros,
            "recent_visits": all_visits[:5],
            "recent_oscs": directorate.oscs.all()[:5],
            "theme_class": theme_class,
            "header_class": header_class,
            "icon_color": icon_color,
        })

        if is_subvencao_only or is_outros:
            oscs = directorate.oscs.all().order_by("name")
            activity_types = (
                directorate.oscs.exclude(activity_type="")
                .values_list("activity_type", flat=True)
                .distinct()
                .order_by("activity_type")
            )
            context["oscs"] = oscs
            context["activity_types"] = list(activity_types)
            context["osc_form"] = OscForm()
            context["dashboard_visits"] = all_visits
            context["dashboard_plan_oscs"] = (
                directorate.oscs.all()
                .prefetch_related("work_plans")
                .order_by("name")
            )
            context["profiles"] = Profile.objects.all().order_by("full_name")
            context["all_directorates"] = Directorate.objects.all().order_by("name")

        # Also try to get form_definition cards for generic directorates
        form_def_raw = directorate.form_definition or []
        form_def = json.loads(form_def_raw) if isinstance(form_def_raw, str) else form_def_raw

        reports = GenericMonitoringReport.objects.filter(
            directorate=directorate, year=selected_year, reference=reference
        ).order_by("month")
        reports_by_month = {r.month: r for r in reports}

        cards = []
        sections = form_def if isinstance(form_def, list) else (form_def.get("sections", []) if isinstance(form_def, dict) else [])
        for section in sections:
            for field in section.get("fields", []):
                if field.get("type") == "number":
                    name = field.get("name")
                    label = field.get("label", name)
                    history = []
                    for m in range(1, 13):
                        r = reports_by_month.get(m)
                        history.append(int(r.payload.get(name, 0) or 0) if r else 0)
                    value = sum(history) if selected_month == "all" else (history[int(selected_month) - 1] if int(selected_month) <= len(history) else 0)
                    cards.append({
                        "label": label,
                        "value": value,
                        "sparkline": build_sparkline(history),
                        "icon": field.get("icon", "activity"),
                        "color": field.get("color", "#3b82f6"),
                        "variation": build_variation(history, selected_month),
                    })

        context["cards"] = cards
        context["period_label"] = build_period_label(selected_year, selected_month)
        context["can_delete"] = self.request.user.is_superuser or (profile and profile.role == "admin")
        return context


class MonitoramentoFormView(MonitoramentoBaseMixin, FormView):
    template_name = "monitoramento/shared/form.html"
    form_class = GenericMonitoringForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        raw_def = self.get_directorate().form_definition or []
        form_def = json.loads(raw_def) if isinstance(raw_def, str) else raw_def
        kwargs["form_definition"] = form_def if isinstance(form_def, list) else (form_def.get("sections", []) if isinstance(form_def, dict) else [])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        month = int(self.request.GET.get("month") or date.today().month)
        year = self.get_year()

        initial["month"] = month
        initial["year"] = year

        report = self._get_existing_report()

        if report:
            initial.update(report.payload)
        return initial

    def _get_existing_report(self):
        directorate = self.get_directorate()
        reference = self.get_reference()
        month = int(self.request.GET.get("month") or date.today().month)
        year = self.get_year()
        return GenericMonitoringReport.objects.filter(
            directorate=directorate, reference=reference, month=month, year=year
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        form = context["form"]
        section_items = []
        raw_def = directorate.form_definition or []
        form_def = json.loads(raw_def) if isinstance(raw_def, str) else raw_def
        sections = form_def if isinstance(form_def, list) else (form_def.get("sections", []) if isinstance(form_def, dict) else [])
        for section in sections:
            title = section.get("title", "Dados")
            fields = [form[f.get("name")] for f in section.get("fields", []) if f.get("name") in form.fields]
            if fields:
                section_items.append({"title": title, "fields": fields})
        existing_report = self._get_existing_report()
        context.update({
            "directorate": directorate,
            "module_title": directorate.name,
            "section_items": section_items,
            "back_url": reverse("monitoramento:home", kwargs={"pk": directorate.pk}),
            "selected_year": self.get_year(),
            "selected_month": int(self.request.GET.get("month") or date.today().month),
            "reference": self.get_reference(),
            "existing_report": existing_report,
            "is_locked": bool(existing_report),
            "is_admin_user": self.is_admin(),
            "month_options": MONTH_OPTIONS,
            "theme_class": get_monitoramento_theme(directorate)[0],
        })
        return context

    def post(self, request, *args, **kwargs):
        if self._get_existing_report():
            messages.error(
                request,
                "Este mês já foi lançado. Peça a um administrador para reabrir antes de preencher novamente.",
            )
            directorate = self.get_directorate()
            month = int(request.GET.get("month") or date.today().month)
            return redirect(
                reverse("monitoramento:form", kwargs={"pk": directorate.pk})
                + f"?year={self.get_year()}&month={month}&ref={self.get_reference()}"
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        directorate = self.get_directorate()
        reference = self.get_reference()
        month = int(form.cleaned_data.pop("month"))
        year = int(form.cleaned_data.pop("year"))
        report, _ = GenericMonitoringReport.objects.get_or_create(
            directorate=directorate, reference=reference, month=month, year=year
        )
        report.payload = form.cleaned_data
        report.save()
        messages.success(self.request, "Dados salvos com sucesso.")
        log_activity(self.request, directorate, "created", "report",
                     f"Indicadores — {build_period_label(year, month)}",
                     url=reverse("monitoramento:data", kwargs={"pk": directorate.pk}) + f"?year={year}")
        return redirect(reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + f"?year={year}")


class MonitoramentoDataView(ExcelExportMixin, MonitoramentoBaseMixin, TemplateView):
    template_name = "monitoramento/shared/data.html"
    export_filename = "monitoramento_dados.xlsx"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reference = self.get_reference()

        raw_def = directorate.form_definition or []
        form_def = json.loads(raw_def) if isinstance(raw_def, str) else raw_def
        sections = form_def if isinstance(form_def, list) else (form_def.get("sections", []) if isinstance(form_def, dict) else [])

        reports = GenericMonitoringReport.objects.filter(
            directorate=directorate, reference=reference, year=selected_year
        )
        reports_by_month = {r.month: r for r in reports}

        available_years = GenericMonitoringReport.objects.filter(
            directorate=directorate, reference=reference
        ).values_list("year", flat=True)

        table_groups = []
        for section in sections:
            fields = [f for f in section.get("fields", []) if f.get("type") == "number"]
            if not fields:
                continue
            rows = []
            for field in fields:
                name = field.get("name")
                label = field.get("label", name)
                values = []
                for month_num, _label in MONTH_LABELS:
                    report = reports_by_month.get(month_num)
                    value = report.payload.get(name, "") if report else ""
                    values.append({
                        "val": value,
                        "sub_id": report.id if report else None,
                        "month": month_num,
                        "year": selected_year,
                    })
                rows.append({"label": label, "key": name, "values": values})
            table_groups.append({"title": section.get("title", "Dados"), "rows": rows})

        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "years_range": build_year_range_from_years(available_years, selected_year),
            "reference": reference,
            "month_labels": [label for _month, label in MONTH_LABELS],
            "table_groups": table_groups,
            "module_title": directorate.name,
            "can_delete": self.is_admin(),
            "back_url": reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + f"?year={selected_year}",
            "form_url": reverse("monitoramento:form", kwargs={"pk": directorate.pk}) + f"?year={selected_year}",
            "theme_class": get_monitoramento_theme(directorate)[0],
        })
        return context

    def export_excel(self):
        ctx = self.get_context_data()
        table_groups = ctx["table_groups"]
        month_labels = ctx["month_labels"]

        sheets = []
        for group in table_groups:
            headers = month_labels
            rows = []
            for row in group["rows"]:
                rows.append([row["label"]] + [v["val"] for v in row["values"]])
            sheets.append({"title": group["title"], "headers": headers, "rows": rows})

        return build_workbook(sheets, self.export_filename)


class MonitoramentoDeleteMonthView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request, *args, **kwargs):
        month = request.POST.get("month")
        year = request.POST.get("year")
        reference = request.POST.get("reference")
        deleted, _ = GenericMonitoringReport.objects.filter(
            directorate_id=kwargs["pk"], reference=reference, month=month, year=year
        ).delete()
        return JsonResponse({"status": "success", "deleted": deleted})

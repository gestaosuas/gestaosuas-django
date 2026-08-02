from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.contrib import messages
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin, NarrativeReportMixin, NarrativeEditorMixin
from apps.core.export import ExcelExportMixin, build_workbook
from apps.core.notifications import log_activity
from apps.core.utils import (
    MONTH_LABELS, MONTH_OPTIONS, build_sparkline,
    build_year_range_from_years, build_variation,
    safe_total, build_series, current_or_total, build_period_label,
)
from apps.directorates.models import Directorate, MonthlyReport
from .models import PopRuaReport
from .forms import PopRuaForm
import json


POPRUA_CARD_FIELDS = [
    ("Total de Atendimentos", "num_atend_total", "users", "#3b82f6"),
    ("Centro de Referência", "num_atend_centro_ref", "building-2", "#06b6d4"),
    ("Abordagem Social", "num_atend_abordagem", "map-pin", "#f59e0b"),
    ("Núcleo Migrante", "num_atend_migracao", "truck", "#10b981"),
    ("Cad. Único", "cr_cad_unico", "id-card", "#8b5cf6"),
    ("Passagens Deferidas", "nm_passagens_deferidas", "ticket", "#ec4899"),
]


class PopRuaBaseMixin(DirectorateAccessMixin):
    def get_directorate(self):
        d = Directorate.objects.filter(name__icontains="População de Rua").first()
        if not d:
            raise Http404("Diretoria de População de Rua não encontrada.")
        return d


class PopRuaDashboardView(TvTemplateMixin, PopRuaBaseMixin, TemplateView):
    template_name = "poprua/dashboard.html"
    tv_template_name = "poprua/tv.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate

        year = int(self.request.GET.get("year", timezone.now().year))
        month_param = self.request.GET.get("month", "all")
        context["selected_year"] = year
        context["selected_month"] = month_param

        reports = PopRuaReport.objects.filter(directorate=directorate, year=year).order_by("month")
        reports_by_month = {r.month: r for r in reports}

        # Cards
        cards = []
        for label, field, icon, color in POPRUA_CARD_FIELDS:
            history = build_series(reports_by_month, field)
            cards.append({
                "label": label,
                "value": current_or_total(reports_by_month, field, month_param),
                "sparkline": build_sparkline(history),
                "icon": icon,
                "color": color,
                "variation": build_variation(history, month_param),
            })
        context["cards"] = cards

        # Chart labels
        months_labels = [label for _, label in MONTH_LABELS]

        # Line chart: Centro Ref, Abordagem, Migração
        context["chart_labels"] = json.dumps(months_labels)
        context["chart_centro"] = json.dumps(build_series(reports_by_month, "num_atend_centro_ref"))
        context["chart_abordagem"] = json.dumps(build_series(reports_by_month, "num_atend_abordagem"))
        context["chart_migracao"] = json.dumps(build_series(reports_by_month, "num_atend_migracao"))

        # Doughnut: Drogas CR vs AR
        drogas_cr = current_or_total(reports_by_month, "cr_b1_drogas", month_param)
        drogas_ar = current_or_total(reports_by_month, "ar_e5_drogas", month_param)
        context["drogas_data"] = json.dumps([drogas_cr, drogas_ar])
        context["drogas_labels"] = json.dumps(["Centro de Referência", "Abordagem Social"])

        # Passagens bar chart
        context["passagens_deferidas"] = json.dumps(build_series(reports_by_month, "nm_passagens_deferidas"))
        context["passagens_indeferidas"] = json.dumps(build_series(reports_by_month, "nm_passagens_indeferidas"))

        # Encaminhamentos bar chart
        context["enc_mercado"] = json.dumps(build_series(reports_by_month, "cr_enc_mercado"))
        context["enc_caps"] = json.dumps(build_series(reports_by_month, "cr_enc_caps"))
        context["enc_saude"] = json.dumps(build_series(reports_by_month, "cr_enc_saude"))
        context["enc_consultorio"] = json.dumps(build_series(reports_by_month, "cr_enc_consultorio"))

        available_years = PopRuaReport.objects.filter(directorate=directorate).values_list("year", flat=True)
        context["years_range"] = build_year_range_from_years(available_years, year)
        context["months_range"] = MONTH_OPTIONS
        return context

class PopRuaDataListView(ExcelExportMixin, PopRuaBaseMixin, TemplateView):
    template_name = "poprua/data_list.html"
    export_filename = "pop_rua_dados.xlsx"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        year = int(self.request.GET.get("year", timezone.now().year))
        
        reports = PopRuaReport.objects.filter(directorate=directorate, year=year).order_by("month")
        reports_dict = {r.month: r for r in reports}
        
        sections = PopRuaForm.section_map
        matrix_data = []
        
        for section_title, fields in sections:
            section_rows = []
            for field_name in fields:
                field_label = PopRuaReport._meta.get_field(field_name).verbose_name or field_name
                
                months_data = []
                total = 0
                for m in range(1, 13):
                    r = reports_dict.get(m)
                    val = getattr(r, field_name, 0) if r else 0
                    if val is None: val = 0
                    months_data.append({"val": val, "sub_id": r.id if r else None, "month": m, "year": year})
                    total += val
                
                section_rows.append({
                    "label": field_label,
                    "key": field_name,
                    "months": months_data,
                    "total": total
                })
            matrix_data.append({"title": section_title, "rows": section_rows})

        context["matrix_data"] = matrix_data
        context["selected_year"] = year
        context["month_headers"] = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        context["years_range"] = range(2023, timezone.now().year + 1)
        context["directorate"] = directorate
        context["can_delete"] = self.is_admin()
        return context

    def export_excel(self):
        ctx = self.get_context_data()
        matrix_data = ctx["matrix_data"]
        month_headers = ctx["month_headers"]

        sheets = []
        for section in matrix_data:
            headers = month_headers + ["TOTAL"]
            rows = []
            for row in section["rows"]:
                rows.append([row["label"]] + [m["val"] for m in row["months"]] + [row["total"]])
            sheets.append({"title": section["title"], "headers": headers, "rows": rows})

        return build_workbook(sheets, self.export_filename)

class PopRuaDeleteMonthView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request, *args, **kwargs):
        directorate = Directorate.objects.filter(name__icontains="População de Rua").first()

        try:
            month = int(request.POST.get("month"))
            year = int(request.POST.get("year"))
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "Mês/ano inválidos."}, status=400)

        deleted, _ = PopRuaReport.objects.filter(
            directorate=directorate, month=month, year=year
        ).delete()
        return JsonResponse({"status": "success", "deleted": deleted})


class PopRuaUpdateView(PopRuaBaseMixin, View):
    def _get_existing_report(self, directorate, month, year):
        return PopRuaReport.objects.filter(directorate=directorate, month=month, year=year).first()

    def get(self, request, pk=None):
        directorate = self.get_directorate()
        report = None
        if pk:
            report = get_object_or_404(PopRuaReport, pk=pk)

        if report:
            month, year = report.month, report.year
        else:
            month = int(request.GET.get("month") or timezone.now().month)
            year = int(request.GET.get("year") or timezone.now().year)

        # Uma linha de PopRuaReport por (diretoria, mês, ano) já representa o
        # mês inteiro "lançado" (ao contrário do CEAI, aqui não há dimensão
        # de unidade dentro de um JSON — a existência da linha já basta).
        existing = self._get_existing_report(directorate, month, year)
        is_locked = bool(existing)

        initial = {}
        if not report:
            initial["year"] = year
            initial["month"] = month

        form = PopRuaForm(instance=report, initial=initial)
        return render(request, "poprua/form.html", {
            "form": form,
            "directorate": directorate,
            "report": report,
            "selected_month": month,
            "selected_year": year,
            "is_locked": is_locked,
            "is_admin_user": self.is_admin(),
            "month_options": MONTH_OPTIONS,
        })

    def post(self, request, pk=None):
        directorate = self.get_directorate()
        report = None

        # Primary check: ID based
        if pk:
            report = get_object_or_404(PopRuaReport, pk=pk)

        form = PopRuaForm(request.POST, instance=report)
        if form.is_valid():
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]

            existing = self._get_existing_report(directorate, month, year)
            if existing:
                # Mês já lançado (linha já existe para diretoria/mês/ano) --
                # rejeita a gravação, mesmo em POST direto. É preciso um
                # administrador "reabrir o mês" (apagar o registro) antes de
                # permitir um novo preenchimento.
                messages.error(
                    request,
                    "Este mês já foi lançado. Peça a um administrador para reabrir antes de preencher novamente.",
                )
                return redirect(
                    reverse("poprua:update_data") + f"?year={year}&month={month}"
                )

            new_report = form.save(commit=False)
            new_report.directorate = directorate
            new_report.created_by = request.user
            new_report.save()
            messages.success(request, "Dados salvos com sucesso no banco de dados!")
            log_activity(request, directorate, "created", "report",
                         f"População em Situação de Rua — {build_period_label(year, month)}",
                         url=reverse("poprua:data_list") + f"?year={year}")
            return redirect("poprua:dashboard")
        else:
            error_msg = "Erro ao salvar dados. Verifique os campos: "
            error_fields = [form.fields[f].label for f in form.errors]
            messages.error(request, error_msg + ", ".join(error_fields))

        return render(request, "poprua/form.html", {
            "form": form,
            "directorate": directorate,
            "report": report,
            "selected_month": form.data.get("month"),
            "selected_year": form.data.get("year"),
            "is_locked": False,
            "is_admin_user": self.is_admin(),
        })

class PopRuaQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request):
        sub_id = request.POST.get("sub_id")
        key = request.POST.get("key")
        value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        
        directorate = Directorate.objects.filter(name__icontains="População de Rua").first()
        
        NUMERIC_TYPES = ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'FloatField', 'DecimalField')
        allowed_keys = {f.name for f in PopRuaReport._meta.get_fields()
                        if hasattr(f, 'get_internal_type') and f.get_internal_type() in NUMERIC_TYPES}
        if key not in allowed_keys:
            return JsonResponse({"error": "Campo não permitido"}, status=400)

        if sub_id and sub_id != "None" and sub_id != "":
            report = get_object_or_404(PopRuaReport, id=sub_id)
        else:
            report, _ = PopRuaReport.objects.get_or_create(
                directorate=directorate,
                month=month,
                year=year,
                defaults={"created_by": request.user},
            )

        setattr(report, key, value)
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})


class PopRuaMonthlyNarrativeView(PopRuaBaseMixin, NarrativeReportMixin, RoleRequiredMixin, TemplateView):
    template_name = "directorates/shared/narrative_report.html"
    setor = "poprua"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_editor_url(self, month, year):
        return f"{reverse('poprua:narrative-editor')}?year={year}&month={month}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = int(self.request.GET.get("month") or timezone.now().month)
        year = int(self.request.GET.get("year") or timezone.now().year)
        hist_year = int(self.request.GET.get("hist_year") or year)
        context.update(self.get_narrative_context(month, year, hist_year))
        context.update({
            "report_label": "População de Rua e Migrantes",
            "theme_class": "theme-blue",
            "back_url": reverse("poprua:dashboard") + f"?year={year}",
        })
        return context


class PopRuaNarrativeEditorView(PopRuaBaseMixin, NarrativeEditorMixin, RoleRequiredMixin, TemplateView):
    template_name = "directorates/shared/narrative_editor.html"
    setor = "poprua"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_view_url(self, month, year):
        return f"{reverse('poprua:monthly-report')}?year={year}&month={month}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = int(self.request.GET.get("month") or timezone.now().month)
        year = int(self.request.GET.get("year") or timezone.now().year)
        context.update(self.get_editor_context(month, year))
        context.update({
            "report_label": "População de Rua e Migrantes",
            "theme_class": "theme-blue",
            "months_range": MONTH_OPTIONS,
            "cancel_url": self.get_view_url(month, year),
        })
        return context

    def post(self, request, *args, **kwargs):
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        directorate = self.save_narrative(request, month, year)
        if directorate is not None:
            log_activity(request, directorate, "finalized", "report",
                         f"Relatorio Mensal Populacao de Rua {build_period_label(year, month)}",
                         url=self.get_view_url(month, year))
        return redirect(self.get_view_url(month, year))

from datetime import date
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View

from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from apps.directorates.models import Directorate, MonthlyReport
from apps.core.export import ExcelExportMixin, build_workbook
from apps.core.utils import (
    MONTH_LABELS, MONTH_LABELS as MONTH_LABELS_ARR, MONTH_OPTIONS,
    build_sparkline, build_column_points, build_period_label,
    build_year_range_from_years, build_variation, safe_total,
    build_series, current_or_total, sum_fields_by_month,
    selected_or_total_fields, build_highlight_badge
)
from .models import SineReport, QualificacaoReport
from .forms import SineReportForm, QualificacaoReportForm

SINE_CARD_FIELDS = [
    ("Inseridos no Mercado", "inseridos_mercado", "briefcase-business", "#3b82f6"),
    ("Entrevistados", "entrevistados", "messages-square", "#06b6d4"),
    ("Vagas de Alto Valor", "vagas_alto_valor", "clipboard-list", "#0ea5e9"),
    ("Primeiro Emprego", "proc_administrativos", "user-check", "#f59e0b"),
]

CP_CARD_FIELDS = [
    ("Concluintes", "resumo_concluintes", "graduation-cap", "#3b82f6"),
    ("Vagas Oferecidas", "resumo_vagas", "briefcase-business", "#06b6d4"),
    ("Taxa de Ocupação (%)", "resumo_taxa_ocupacao", "trending-up", "#8b5cf6"),
    ("Cursos Total", "resumo_cursos", "book-open", "#f59e0b"),
    ("Turmas Total", "resumo_turmas", "users", "#10b981"),
]

CP_ATENDIMENTOS_FIELDS = [
    "cp_morumbi_atendimentos", "cp_lagoinha_atendimentos", "cp_campo_alegre_atendimentos",
    "cp_luizote_1_atendimentos", "cp_luizote_2_atendimentos", "cp_tocantis_atendimentos",
    "cp_planalto_atendimentos", "maravilha_atendimentos", "unitech_atendimentos", "onibus_atendimentos"
]

class SineCpBaseMixin(DirectorateAccessMixin):
    def get_directorate(self):
        directorate = Directorate.objects.filter(name__icontains="sine").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="qualific").first()
        if not directorate:
            raise Http404("A diretoria de SINE e Qualificacao Profissional nao foi encontrada.")
        return directorate

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"


class SineCpHomeView(TvTemplateMixin, SineCpBaseMixin, DetailView):
    template_name = "sinecp/home.html"
    tv_template_name = "sinecp/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.object
        selected_year = self.get_year()
        selected_month = self.get_month()
        active_tab = self.request.GET.get("tab", "sine")
        
        # SINE Data
        sine_reports = SineReport.objects.filter(directorate=directorate, year=selected_year).order_by("month")
        sine_by_month = {r.month: r for r in sine_reports}
        
        sine_cards = []
        for label, field, icon, color in SINE_CARD_FIELDS:
            history = build_series(sine_by_month, field)
            sine_cards.append({
                "label": label,
                "value": current_or_total(sine_by_month, field, selected_month),
                "history": history,
                "sparkline": build_sparkline(history),
                "icon": icon,
                "color": color,
                "variation": build_variation(history, selected_month),
            })

        # CP Data
        cp_reports = QualificacaoReport.objects.filter(directorate=directorate, year=selected_year).order_by("month")
        cp_by_month = {r.month: r for r in cp_reports}
        
        cp_cards = []
        for label, field, icon, color in CP_CARD_FIELDS:
            if field == "resumo_taxa_ocupacao":
                # Taxa de ocupação: média quando ano inteiro, valor do mês quando específico
                monthly_vals = [float(safe_total(cp_by_month.get(m), field)) for m, _ in MONTH_LABELS]
                nonzero = [v for v in monthly_vals if v > 0]
                if selected_month == "all":
                    val = round(sum(nonzero) / len(nonzero), 1) if nonzero else 0
                else:
                    try:
                        val = round(monthly_vals[int(selected_month) - 1], 1)
                    except (ValueError, IndexError):
                        val = 0
                history = [round(v, 1) for v in monthly_vals]
            else:
                val = current_or_total(cp_by_month, field, selected_month)
                history = build_series(cp_by_month, field)
            cp_cards.append({
                "label": label,
                "value": val,
                "history": history,
                "sparkline": build_sparkline(history),
                "icon": icon,
                "color": color,
                "variation": build_variation(history, selected_month),
            })

        # Chart Data
        def sum_online(reports_by_month, field1, field2):
            return [safe_total(reports_by_month.get(m), field1) + safe_total(reports_by_month.get(m), field2) for m, _ in MONTH_LABELS]

        sine_chart_data = {
            "labels": [label for _, label in MONTH_LABELS],
            "trabalhador_values": sum_online(sine_by_month, "atend_trabalhador", "atend_online_trabalhador"),
            "empregador_values": sum_online(sine_by_month, "atend_empregador", "atend_online_empregador"),
            "services_labels": ["Orientação", "Carteira", "Pro. Seletivo", "Currículos", "Seguro"],
            "services_values": [
                current_or_total(sine_by_month, "orientacao_profissional", selected_month),
                current_or_total(sine_by_month, "carteira_digital", selected_month),
                current_or_total(sine_by_month, "processo_seletivo", selected_month),
                current_or_total(sine_by_month, "curriculos", selected_month),
                current_or_total(sine_by_month, "seguro_desemprego", selected_month),
            ]
        }

        cp_chart_data = {
            "labels": [label for _, label in MONTH_LABELS],
            "concluintes_values": build_series(cp_by_month, "resumo_concluintes"),
            "atendimentos_values": [sum(getattr(cp_by_month.get(m), f, 0) or 0 for f in CP_ATENDIMENTOS_FIELDS) for m, _ in MONTH_LABELS],
            "gender_labels": ["Masculino", "Feminino"],
            "gender_values": [
                current_or_total(cp_by_month, "resumo_homens", selected_month),
                current_or_total(cp_by_month, "resumo_mulheres", selected_month)
            ],
            "gender_colors": ["#3b82f6", "#ec4899"]
        }

        context.update({
            "selected_year": selected_year,
            "selected_month": selected_month,
            "months_range": MONTH_OPTIONS,
            "active_tab": active_tab,
            "active_cards": sine_cards if active_tab == "sine" else cp_cards,
            "sine_chart_data": sine_chart_data,
            "cp_chart_data": cp_chart_data,
            "sine_total_attendance": current_or_total(sine_by_month, "atend_trabalhador", selected_month) + current_or_total(sine_by_month, "atend_empregador", selected_month),
            "cp_peak_concluintes": max(cp_chart_data["concluintes_values"]) if any(cp_chart_data["concluintes_values"]) else 0,
            "cp_total_interactions": sum(cp_chart_data["atendimentos_values"]),
            "cp_gender": [
                {"label": "Masc", "value": cp_chart_data["gender_values"][0], "color": "#3b82f6"},
                {"label": "Fem", "value": cp_chart_data["gender_values"][1], "color": "#ec4899"},
            ] if any(cp_chart_data["gender_values"]) else [],
            "years_range": build_year_range_from_years([], selected_year),
        })
        return context

# Rest of the views (Forms, Data, QuickEdit)
class SharedCreateUpdateView(SineCpBaseMixin, FormView):
    template_name = "sinecp/shared/form.html"
    form_class = None
    success_view_name = ""
    report_title = ""
    delete_month_view_name = ""

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = int(self.request.GET.get("month") or date.today().month)
        initial["year"] = self.get_year()
        report = self.get_existing_report()
        if report:
            for field_name in self.form_class.Meta.model._meta.fields:
                if field_name.name in self.form_class.base_fields:
                    initial[field_name.name] = getattr(report, field_name.name)
        return initial

    def get_existing_report(self):
        directorate = self.get_directorate()
        month = int(self.request.GET.get("month") or date.today().month)
        year = self.get_year()
        return self.form_class.Meta.model.objects.filter(directorate=directorate, month=month, year=year).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        section_items = []
        for section_title, field_names in self.form_class.section_map:
            section_items.append({
                "title": section_title,
                "fields": [form[field_name] for field_name in field_names],
            })
        context["directorate"] = self.get_directorate()
        context["selected_year"] = self.get_year()
        context["selected_month"] = int(self.request.GET.get("month") or date.today().month)
        context["section_items"] = section_items
        context["module_title"] = self.report_title
        existing_report = self.get_existing_report()
        context["existing_report"] = existing_report
        context["is_locked"] = bool(existing_report)
        context["is_admin_user"] = self.is_admin()
        context["delete_month_url"] = reverse(self.delete_month_view_name)
        context["month_options"] = MONTH_OPTIONS
        return context

    def post(self, request, *args, **kwargs):
        if self.get_existing_report():
            messages.error(
                request,
                "Este mês já foi lançado. Peça a um administrador para reabrir antes de preencher novamente.",
            )
            month = int(request.GET.get("month") or date.today().month)
            return redirect(f"{request.path}?year={self.get_year()}&month={month}")
        return super().post(request, *args, **kwargs)

class SineCreateUpdateView(SharedCreateUpdateView):
    form_class = SineReportForm
    success_view_name = "sinecp:sine-data"
    report_title = "SINE"
    delete_month_view_name = "sinecp:sine-delete-month"

    def form_valid(self, form):
        directorate = self.get_directorate()
        month = form.cleaned_data["month"]
        year = form.cleaned_data["year"]
        report, _created = SineReport.objects.get_or_create(
            directorate=directorate, month=month, year=year,
            defaults={"created_at": timezone.now(), "updated_at": timezone.now()},
        )
        for field_name, value in form.cleaned_data.items():
            setattr(report, field_name, value)
        report.user_external_id = None
        report.updated_at = timezone.now()
        report.save()
        messages.success(self.request, "Dados salvos.")
        return redirect(reverse(self.success_view_name) + f"?year={year}")

class QualificacaoCreateUpdateView(SharedCreateUpdateView):
    form_class = QualificacaoReportForm
    success_view_name = "sinecp:qualificacao-data"
    report_title = "Qualificacao"
    delete_month_view_name = "sinecp:qualificacao-delete-month"

    def form_valid(self, form):
        directorate = self.get_directorate()
        month = form.cleaned_data["month"]
        year = form.cleaned_data["year"]
        report, _created = QualificacaoReport.objects.get_or_create(
            directorate=directorate, month=month, year=year,
            defaults={"created_at": timezone.now(), "updated_at": timezone.now()},
        )
        for field_name, value in form.cleaned_data.items():
            setattr(report, field_name, value)
        report.updated_at = timezone.now()
        report.save()
        messages.success(self.request, "Dados salvos.")
        return redirect(reverse(self.success_view_name) + f"?year={year}")

class SharedDataView(SineCpBaseMixin, TemplateView):
    template_name = "sinecp/shared/data.html"
    model = None
    form_class = None
    module_title = ""
    back_tab = "sine"
    form_view_name = ""
    monthly_report_view_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reports = {r.month: r for r in self.model.objects.filter(directorate=directorate, year=selected_year)}
        table_groups = []
        for title, fields in self.form_class.section_map:
            table_groups.append({
                "title": title,
                "rows": [{
                    "label": self.form_class.labels.get(f, f),
                    "key": f,
                    "values": [{"val": getattr(reports.get(m), f, "") if reports.get(m) else "", "sub_id": reports.get(m).id if reports.get(m) else None, "month": m, "year": selected_year} for m, _ in MONTH_LABELS],
                } for f in fields]
            })
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "month_labels": [label for _, label in MONTH_LABELS],
            "table_groups": table_groups,
            "module_title": self.module_title,
            "can_delete": self.is_admin(),
            "back_url": reverse("sinecp:home") + f"?tab={self.back_tab}&year={selected_year}",
            "form_url": reverse(self.form_view_name) + f"?year={selected_year}",
            "monthly_report_url": reverse(self.monthly_report_view_name) + f"?year={selected_year}",
        })
        return context

    def export_excel(self):
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reports = {
            r.month: r
            for r in self.model.objects.filter(
                directorate=directorate, year=selected_year
            )
        }
        month_labels = [label for _, label in MONTH_LABELS_ARR]
        sheets = []
        for title, fields in self.form_class.section_map:
            rows = []
            for f in fields:
                row = [self.form_class.labels.get(f, f)]
                for m, _ in MONTH_LABELS_ARR:
                    r = reports.get(m)
                    row.append(getattr(r, f, "") if r else "")
                rows.append(row)
            sheets.append({"title": title, "headers": month_labels, "rows": rows})
        return build_workbook(sheets, self.export_filename)


class SineDataView(ExcelExportMixin, SharedDataView):
    model = SineReport
    form_class = SineReportForm
    module_title = "SINE"
    export_filename = "SINE.xlsx"
    back_tab = "sine"
    form_view_name = "sinecp:sine-form"
    monthly_report_view_name = "sinecp:sine-monthly-report"

class QualificacaoDataView(ExcelExportMixin, SharedDataView):
    model = QualificacaoReport
    form_class = QualificacaoReportForm
    module_title = "Qualificacao Profissional"
    export_filename = "Qualificacao_Profissional.xlsx"
    back_tab = "cp"
    form_view_name = "sinecp:qualificacao-form"
    monthly_report_view_name = "sinecp:qualificacao-monthly-report"

class SharedMonthlyNarrativeView(SineCpBaseMixin, TemplateView):
    template_name = "sinecp/shared/monthly_report.html"
    setor = ""
    module_title = ""
    back_tab = "sine"
    form_view_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        month = int(self.request.GET.get("month") or date.today().month)
        qs = MonthlyReport.objects.filter(directorate=directorate, setor=self.setor, year=selected_year, month=month)
        if self.is_agente():
            qs = qs.filter(user_external_id=self.request.user.pk)
        report = qs.first()
        history_qs = MonthlyReport.objects.filter(directorate=directorate, setor=self.setor).order_by("-year", "-month")
        if self.is_agente():
            history_qs = history_qs.filter(user_external_id=self.request.user.pk)
        history = history_qs[:8]
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "selected_month": month,
            "months_range": MONTH_OPTIONS,
            "monthly_report": report,
            "history": history,
            "module_title": self.module_title,
            "back_url": reverse("sinecp:home") + f"?tab={self.back_tab}&year={selected_year}",
            "reports_url": reverse(self.form_view_name),
        })
        return context

class SineMonthlyNarrativeView(SharedMonthlyNarrativeView):
    setor = "sine"; module_title = "SINE"; back_tab = "sine"; form_view_name = "sinecp:sine-reports"

class QualificacaoMonthlyNarrativeView(SharedMonthlyNarrativeView):
    setor = "centros"; module_title = "Qualificacao"; back_tab = "cp"; form_view_name = "sinecp:qualificacao-reports"

class SharedNarrativeListView(SineCpBaseMixin, TemplateView):
    template_name = "sinecp/shared/reports.html"
    setor = ""; module_title = ""; back_tab = "sine"; monthly_view_name = ""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reports = MonthlyReport.objects.filter(directorate=directorate, setor=self.setor, year=selected_year).order_by("-year", "-month")
        if self.is_agente():
            reports = reports.filter(user_external_id=self.request.user.pk)
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "module_title": self.module_title,
            "reports": reports,
            "can_delete": self.is_admin(),
            "back_url": reverse("sinecp:home") + f"?tab={self.back_tab}&year={selected_year}",
            "monthly_report_base_url": reverse(self.monthly_view_name),
        })
        return context

class SineNarrativeListView(SharedNarrativeListView):
    setor = "sine"; module_title = "SINE"; back_tab = "sine"; monthly_view_name = "sinecp:sine-monthly-report"

class QualificacaoNarrativeListView(SharedNarrativeListView):
    setor = "centros"; module_title = "Qualificacao"; back_tab = "cp"; monthly_view_name = "sinecp:qualificacao-monthly-report"

class SharedQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]
    model = None
    def post(self, request):
        sub_id = request.POST.get("sub_id"); key = request.POST.get("key"); value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month")); year = int(request.POST.get("year"))
        directorate = Directorate.objects.filter(name__icontains="sine").first()
        if not directorate: directorate = Directorate.objects.filter(name__icontains="qualific").first()
        NUMERIC_TYPES = ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'FloatField', 'DecimalField')
        allowed_keys = {f.name for f in self.model._meta.get_fields()
                        if hasattr(f, 'get_internal_type') and f.get_internal_type() in NUMERIC_TYPES}
        if key not in allowed_keys:
            return JsonResponse({"error": "Campo não permitido"}, status=400)

        if sub_id and sub_id != "None" and sub_id != "":
            report = get_object_or_404(self.model, id=sub_id)
        else:
            report, _ = self.model.objects.get_or_create(
                directorate=directorate, month=month, year=year,
                defaults={"created_at": timezone.now(), "updated_at": timezone.now()},
            )
        setattr(report, key, value)
        report.updated_at = timezone.now()
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

class SineQuickEditView(SharedQuickEditView): model = SineReport
class QualificacaoQuickEditView(SharedQuickEditView): model = QualificacaoReport

class SharedDeleteMonthView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]
    model = None

    def post(self, request, *args, **kwargs):
        month = request.POST.get("month")
        year = request.POST.get("year")
        directorate = Directorate.objects.filter(name__icontains="sine").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="qualific").first()
        deleted, _ = self.model.objects.filter(
            directorate=directorate, month=month, year=year
        ).delete()
        return JsonResponse({"status": "success", "deleted": deleted})

class SineDeleteMonthView(SharedDeleteMonthView): model = SineReport
class QualificacaoDeleteMonthView(SharedDeleteMonthView): model = QualificacaoReport

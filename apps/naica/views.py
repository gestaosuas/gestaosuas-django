import uuid
from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View
from django.http import JsonResponse
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin

from apps.directorates.models import Directorate, MonthlyReport
from apps.core.utils import (
    MONTH_LABELS, MONTH_OPTIONS, build_sparkline, build_column_points,
    build_period_label, build_year_range_from_years, build_variation
)
from .models import NaicaReport
from .forms import NaicaReportForm

NAICA_UNITS = [
    "Canaã", "Jdm Célia", "Lagoinha", "Luizote", "Mansour",
    "Marta Helena", "Morumbi", "Pequis", "Tibery", "Tocantins", "Tapuirama",
]

NAICA_CARD_FIELDS = [
    ("Total em Acompanhamento", "total_atendidas", "users", "#3b82f6"),
    ("Taxa de Ocupacao", "__taxa__", "pie-chart", "#8b5cf6"),
    ("Admitidos Masculino", "inseridos_masc", "user-plus", "#3b82f6"),
    ("Admitidos Feminino", "inseridos_fem", "user-plus", "#f472b6"),
]

NAICA_UNIT_CAPACITY = 120


class NaicaBaseMixin(DirectorateAccessMixin):
    monthly_report_sector = "naica"

    def get_directorate(self):
        directorate = Directorate.objects.filter(pk=self.kwargs["pk"]).first()
        if not directorate:
            raise Http404("Diretoria nao encontrada.")
        return directorate

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"

    def get_month_number(self):
        month_value = self.request.GET.get("month")
        return int(month_value) if month_value and month_value != "all" else date.today().month

    def get_unit_name(self):
        return self.request.GET.get("unit") or "all"


class NaicaHomeView(TvTemplateMixin, NaicaBaseMixin, DetailView):
    template_name = "naica/home.html"
    tv_template_name = "naica/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.object
        selected_year = self.get_year()
        selected_month = self.get_month()
        selected_unit = self.get_unit_name()
        visible_units = self.filter_units(NAICA_UNITS)

        reports = NaicaReport.objects.filter(
            directorate=directorate, year=selected_year
        ).order_by("month", "unit_name")

        reports_by_month_unit = {}
        all_reports_list = list(reports)
        for report in all_reports_list:
            key = (report.month, report.unit_name)
            reports_by_month_unit[key] = report

        available_years = NaicaReport.objects.filter(
            directorate=directorate
        ).values_list("year", flat=True)

        month_labels = [label for _month_num, label in MONTH_LABELS]

        def get_unit_history(field_name):
            history = [0] * 12
            if selected_unit == "all":
                for month_num in range(1, 13):
                    total = 0
                    for unit in visible_units:
                        report = reports_by_month_unit.get((month_num, unit))
                        if report:
                            total += int(getattr(report, field_name, 0) or 0)
                    history[month_num - 1] = total
            else:
                for month_num in range(1, 13):
                    report = reports_by_month_unit.get((month_num, selected_unit))
                    history[month_num - 1] = int(getattr(report, field_name, 0) or 0) if report else 0
            return history

        def get_unit_value(field_name):
            if selected_month == "all":
                return sum(get_unit_history(field_name))
            report = reports_by_month_unit.get((int(selected_month), selected_unit)) if selected_unit != "all" else None
            if selected_unit != "all":
                return int(getattr(report, field_name, 0) or 0) if report else 0
            else:
                total = 0
                for unit in visible_units:
                    r = reports_by_month_unit.get((int(selected_month), unit))
                    if r:
                        total += int(getattr(r, field_name, 0) or 0)
                return total

        total_atendidas_hist = get_unit_history("total_atendidas")
        inseridos_masc_hist = get_unit_history("inseridos_masc")
        inseridos_fem_hist = get_unit_history("inseridos_fem")
        desligados_masc_hist = get_unit_history("desligados_masc")
        desligados_fem_hist = get_unit_history("desligados_fem")

        total_atendidas_val = get_unit_value("total_atendidas")
        unit_count = len(visible_units) if selected_unit == "all" else 1
        capacidade_total = NAICA_UNIT_CAPACITY * unit_count
        taxa_ocupacao = round((total_atendidas_val / capacidade_total) * 100, 1) if capacidade_total > 0 else 0

        inseridos_total_hist = [inseridos_masc_hist[i] + inseridos_fem_hist[i] for i in range(12)]
        desligados_total_hist = [desligados_masc_hist[i] + desligados_fem_hist[i] for i in range(12)]

        cards = []
        for index, field_info in enumerate(NAICA_CARD_FIELDS):
            label, field_name, icon, color = field_info
            if field_name == "__taxa__":
                value = taxa_ocupacao
                history = total_atendidas_hist
                suffix = "%"
            else:
                value = get_unit_value(field_name)
                history = get_unit_history(field_name)
                suffix = ""
            cards.append({
                "label": label,
                "value": value,
                "suffix": suffix,
                "sparkline": build_sparkline(history),
                "icon": icon,
                "color": color,
                "variation": build_variation(history, selected_month),
            })

        monthly_reports = MonthlyReport.objects.filter(
            directorate=directorate,
            setor="naica",
        ).order_by("-year", "-month", "-created_at")[:6]

        context.update({
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_unit": selected_unit,
            "months_range": MONTH_OPTIONS,
            "years_range": build_year_range_from_years(available_years, selected_year),
            "naica_units": visible_units,
            "cards": cards,
            "reports": all_reports_list,
            "line_chart_total": build_column_points(total_atendidas_hist),
            "adm_desl_points": [
                {
                    "label": month_labels[i],
                    "admitidos": inseridos_total_hist[i],
                    "desligados": desligados_total_hist[i],
                }
                for i in range(12)
            ],
            "month_labels": month_labels,
            "period_label": build_period_label(selected_year, selected_month),
            "monthly_narratives": monthly_reports,
        })
        return context


class NaicaCreateUpdateView(NaicaBaseMixin, FormView):
    template_name = "naica/form.html"
    form_class = NaicaReportForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        unit = self.request.GET.get("unit") or ""
        if unit:
            initial["unit_name"] = unit
        report = self._get_existing_report()
        if report:
            for model_field in self.form_class.Meta.model._meta.fields:
                if model_field.name in self.form_class.base_fields:
                    initial[model_field.name] = getattr(report, model_field.name)
            initial["unit_name"] = report.unit_name
        return initial

    def _get_existing_report(self):
        directorate = self.get_directorate()
        month_val = self.get_month_number()
        year_val = self.get_year()
        unit_val = self.request.GET.get("unit") or ""
        if unit_val:
            return NaicaReport.objects.filter(
                directorate=directorate, month=month_val, year=year_val, unit_name=unit_val
            ).first()
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        directorate = self.get_directorate()
        section_items = []
        for section_title, field_names in self.form_class.section_map:
            section_items.append({
                "title": section_title,
                "fields": [form[field_name] for field_name in field_names],
            })
        context.update({
            "directorate": directorate,
            "selected_year": self.get_year(),
            "selected_month": self.get_month_number(),
            "section_items": section_items,
            "existing_report": self._get_existing_report(),
            "naica_units": self.filter_units(NAICA_UNITS),
            "selected_unit": self.request.GET.get("unit") or "",
        })
        return context

    def form_valid(self, form):
        directorate = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        unit_name = self.request.POST.get("unit_name", "") or self.request.GET.get("unit", "")

        if not unit_name:
            messages.error(self.request, "Selecione uma unidade NAICA.")
            return redirect(
                reverse("naica:form", kwargs={"pk": directorate.pk})
                + f"?year={year_val}&month={month_val}"
            )

        report, _ = NaicaReport.objects.get_or_create(
            directorate=directorate,
            month=month_val,
            year=year_val,
            unit_name=unit_name,
            defaults={"user_id": self.request.user.pk},
        )
        for field_name, value in form.cleaned_data.items():
            setattr(report, field_name, value)
        report.status = "submitted"
        report.user_id = self.request.user.pk
        report.save()
        messages.success(self.request, f"Dados do NAICA {unit_name} salvos com sucesso.")
        return redirect(
            reverse("naica:home", kwargs={"pk": directorate.pk})
            + f"?year={year_val}&month={month_val}&unit={unit_name}"
        )


class NaicaDataView(NaicaBaseMixin, TemplateView):
    template_name = "naica/data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()

        reports = NaicaReport.objects.filter(
            directorate=directorate, year=selected_year
        ).order_by("unit_name", "month")

        reports_by_unit_month = {}
        for report in reports:
            key = (report.unit_name, report.month)
            reports_by_unit_month[key] = report

        visible_units = self.filter_units(NAICA_UNITS)
        units_tables = []
        for unit in visible_units:
            groups = []
            for title, fields in NaicaReportForm.section_map:
                rows = []
                for field_name in fields:
                    month_values = []
                    for month_num in range(1, 13):
                        report = reports_by_unit_month.get((unit, month_num))
                        month_values.append({
                            "val": getattr(report, field_name, "") if report else "",
                            "sub_id": report.id if report else None,
                            "month": month_num,
                            "year": selected_year,
                            "unit": unit
                        })
                    rows.append({
                        "label": NaicaReportForm.labels.get(field_name, field_name),
                        "key": field_name,
                        "values": month_values,
                    })
                groups.append({"title": title, "rows": rows})
            units_tables.append({"unit": unit, "groups": groups})

        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "month_labels": [label for _month, label in MONTH_LABELS],
            "naica_units": visible_units,
            "units_tables": units_tables,
            "can_delete": self.is_admin(),
        })
        return context


class NaicaMonthlyNarrativeView(NaicaBaseMixin, TemplateView):
    template_name = "naica/monthly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        month_val = self.get_month_number()
        qs = MonthlyReport.objects.filter(
            directorate=directorate,
            setor="naica",
            year=selected_year,
            month=month_val,
        )
        if self.is_agente():
            qs = qs.filter(user_external_id=self.request.user.pk)
        report = qs.first()

        history_qs = MonthlyReport.objects.filter(directorate=directorate, setor="naica").order_by("-year", "-month", "-created_at")
        if self.is_agente():
            history_qs = history_qs.filter(user_external_id=self.request.user.pk)
        history = history_qs[:8]

        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "selected_month": month_val,
            "monthly_report": report,
            "history": history,
            "back_url": reverse("naica:home", kwargs={"pk": directorate.pk}) + f"?year={selected_year}",
        })
        return context


class NaicaNarrativeListView(NaicaBaseMixin, TemplateView):
    template_name = "naica/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reports = MonthlyReport.objects.filter(
            directorate=directorate,
            setor="naica",
        ).order_by("-year", "-month", "-created_at")
        if selected_year:
            reports = reports.filter(year=selected_year)
        if self.is_agente():
            reports = reports.filter(user_external_id=self.request.user.pk)
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "reports": reports,
            "can_delete": self.is_admin(),
            "back_url": reverse("naica:home", kwargs={"pk": directorate.pk}) + f"?year={selected_year}",
            "monthly_report_base_url": reverse("naica:monthly-report", kwargs={"pk": directorate.pk}),
        })
        return context

class NaicaQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request):
        sub_id = request.POST.get("sub_id")
        key = request.POST.get("key")
        value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        unit = request.POST.get("unit")
        
        # Tenta encontrar a diretoria pelo nome de forma robusta
        directorate = Directorate.objects.filter(name__icontains="NAICA").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="Proteção Social Especial").first()
        
        if sub_id and sub_id != "None" and sub_id != "":
            report = get_object_or_404(NaicaReport, id=sub_id)
        else:
            report, _ = NaicaReport.objects.get_or_create(
                directorate=directorate,
                month=month,
                year=year,
                unit_name=unit
            )

        setattr(report, key, value)
        if not report.user_id:
            import uuid
            report.user_id = uuid.uuid4()
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

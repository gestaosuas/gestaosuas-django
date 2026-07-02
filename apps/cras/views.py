from datetime import datetime, date
import uuid
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View
from django.utils import timezone

from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from apps.directorates.models import Directorate, MonthlyReport
from apps.core.utils import (
    MONTH_LABELS, MONTH_OPTIONS, build_sparkline, build_column_points,
    build_period_label, build_year_range_from_years, build_variation,
    strip_accents
)
from .models import CrasReport
from .forms import CrasReportForm

CRAS_UNITS = [
    "CAMPO ALEGRE", "CUSTÓDIO PEREIRA", "JARDIM BRASÍLIA", "JARDIM CÉLIA", 
    "MANSOUR", "MARTA HELENA", "MORUMBI", "SÃO JORGE", "TAPUIRAMA", 
    "SHOPPING PARK", "PEQUIS", "CANAÃ", "TOCANTINS"
]

CRAS_CARD_FIELDS = [
    ("Atendimentos", "atendimentos", "phone-call", "#3b82f6"),
    ("Cadastros Novos", "cadastros_novos", "user-plus", "#10b981"),
    ("Recadastros", "recadastros", "refresh-cw", "#f59e0b"),
    ("Famílias Admitidas", "admitidas", "home", "#8b5cf6"),
    ("Famílias Desligadas", "desligadas", "user-minus", "#ef4444"),
    ("Mês Anterior", "anterior", "arrow-left", "#64748b"),
    ("Atual", "atual", "activity", "#4338ca"),
    ("Retenção", "__retencao__", "shield-check", "#06b6d4"),
]

class CrasBaseMixin(DirectorateAccessMixin):
    monthly_report_sector = "cras"

    def get_directorate(self):
        directorate = Directorate.objects.filter(pk=self.kwargs.get("pk")).first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="CRAS").first()
        if not directorate:
            raise Http404("Diretoria de CRAS nao encontrada.")
        return directorate

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"

    def get_month_number(self):
        month_value = self.request.GET.get("month")
        return int(month_value) if month_value and month_value != "all" else date.today().month


class CrasHomeView(TvTemplateMixin, CrasBaseMixin, DetailView):
    template_name = "cras/home.html"
    tv_template_name = "cras/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.object
        selected_year = self.get_year()
        selected_month = self.get_month()
        selected_unit = self.request.GET.get("unit") or "all"

        # Filtra unidades pelo que o usuário tem acesso
        visible_units = self.filter_units(CRAS_UNITS)

        reports = CrasReport.objects.filter(directorate=directorate, year=selected_year)
        available_years = sorted(list(set(CrasReport.objects.filter(directorate=directorate).values_list("year", flat=True))), reverse=True)
        if not available_years: available_years = [selected_year]

        reports_by_month_unit = {}
        for r in reports:
            unit_key = strip_accents(r.unit_name).upper()
            reports_by_month_unit[(r.month, unit_key)] = r

        month_labels = [label for _, label in MONTH_LABELS]

        def get_unit_history(field_name):
            history = []
            for m in range(1, 13):
                if selected_unit != "all":
                    unit_key = strip_accents(selected_unit).upper()
                    r = reports_by_month_unit.get((m, unit_key))
                    history.append(int(getattr(r, field_name, 0) or 0) if r else 0)
                else:
                    total = 0
                    for unit in visible_units:
                        unit_key = strip_accents(unit).upper()
                        r = reports_by_month_unit.get((m, unit_key))
                        if r: total += int(getattr(r, field_name, 0) or 0)
                    history.append(total)
            return history

        def get_unit_value(field_name):
            if selected_month == "all":
                return sum(get_unit_history(field_name))
            try:
                month_val = int(selected_month)
            except (ValueError, TypeError):
                month_val = date.today().month

            if selected_unit != "all":
                unit_key = strip_accents(selected_unit).upper()
                report = reports_by_month_unit.get((month_val, unit_key))
                return int(getattr(report, field_name, 0) or 0) if report else 0
            total = 0
            for unit in visible_units:
                unit_key = strip_accents(unit).upper()
                r = reports_by_month_unit.get((month_val, unit_key))
                if r: total += int(getattr(r, field_name, 0) or 0)
            return total

        atual_hist = get_unit_history("atual")

        cards = []
        for label, field_name, icon, color in CRAS_CARD_FIELDS:
            if field_name == "__retencao__":
                atual_val = get_unit_value("atual")
                deslig_val = get_unit_value("desligadas")
                value = round(((atual_val - deslig_val) / atual_val) * 100, 1) if atual_val > 0 else 0
                suffix = "%"
                history = atual_hist
            else:
                value = get_unit_value(field_name)
                suffix = ""
                history = get_unit_history(field_name)
            cards.append({
                "label": label,
                "value": value,
                "suffix": suffix,
                "sparkline": build_sparkline(history),
                "icon": icon,
                "color": color,
                "variation": build_variation(history, selected_month),
            })

        monthly_reports = MonthlyReport.objects.filter(directorate=directorate, setor="cras").order_by("-year", "-month")[:6]

        context.update({
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_unit": selected_unit,
            "months_range": MONTH_OPTIONS,
            "years_range": build_year_range_from_years(available_years, selected_year),
            "cras_units": visible_units,
            "cards": cards,
            "reports": list(reports),
            "line_chart_cadastros": build_column_points(get_unit_history("cadastros_novos")),
            "line_chart_recadastros": build_column_points(get_unit_history("recadastros")),
            "line_chart_admitidas": build_column_points(get_unit_history("admitidas")),
            "line_chart_desligadas": build_column_points(get_unit_history("desligadas")),
            "line_chart_atendimentos": build_column_points(get_unit_history("atendimentos")),
            "line_chart_atual": build_column_points(atual_hist),
            "month_labels": month_labels,
            "period_label": build_period_label(selected_year, selected_month),
            "monthly_narratives": monthly_reports,
        })
        return context


class CrasCreateUpdateView(CrasBaseMixin, FormView):
    template_name = "cras/form.html"
    form_class = CrasReportForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        unit = self.request.GET.get("unit") or ""
        if unit: initial["unit_name"] = unit
        report = self._get_existing_report()
        if report:
            for f in self.form_class.Meta.model._meta.fields:
                if f.name in self.form_class.base_fields and f.name != "unit_name":
                    initial[f.name] = getattr(report, f.name)
            initial["unit_name"] = report.unit_name
        return initial

    def _get_existing_report(self):
        directorate = self.get_directorate()
        unit_val = self.request.GET.get("unit") or ""
        if unit_val:
            return CrasReport.objects.filter(directorate=directorate, month=self.get_month_number(), year=self.get_year(), unit_name=unit_val).first()
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        section_items = [{"title": t, "fields": [form[f] for f in fs]} for t, fs in self.form_class.section_map]
        # Add RMA section with the file field
        section_items.append({"title": "ANEXOS", "fields": [form["rma_file"]]})
        existing = self._get_existing_report()
        context.update({
            "directorate": self.get_directorate(), "selected_year": self.get_year(), "selected_month": self.get_month_number(),
            "section_items": section_items, "existing_report": existing,
            "cras_units": self.filter_units(CRAS_UNITS), "selected_unit": self.request.GET.get("unit") or "",
            "existing_rma": existing.rma_url if existing else None,
        })
        return context

    def form_valid(self, form):
        directorate = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        unit_name = self.request.POST.get("unit_name", "") or self.request.GET.get("unit", "")
        if not unit_name:
            messages.error(self.request, "Selecione uma unidade CRAS.")
            return redirect(reverse("cras:form", kwargs={"pk": directorate.pk}) + f"?year={year_val}&month={month_val}")
        report, _ = CrasReport.objects.get_or_create(directorate=directorate, month=month_val, year=year_val, unit_name=unit_name)
        for field_name, value in form.cleaned_data.items():
            if field_name == "rma_file":
                continue
            setattr(report, field_name, value)
        # Registra quem salvou
        report.user_external_id = self.request.user.pk
        # Handle RMA file upload
        rma_file = form.cleaned_data.get("rma_file")
        if rma_file:
            import uuid as _uuid, os
            from django.conf import settings
            from django.core.files.storage import default_storage
            ext = os.path.splitext(rma_file.name)[1]
            m = int(month_val)
            filename = f"rma/{directorate.pk}/{unit_name}/{year_val}_{m:02d}_{_uuid.uuid4().hex[:8]}{ext}"
            saved_path = default_storage.save(filename, rma_file)
            report.rma_url = settings.MEDIA_URL + saved_path
            report.anexo_rma = rma_file.name
        report.updated_at = datetime.now()
        report.save()
        messages.success(self.request, f"Dados do CRAS {unit_name} salvos.")
        return redirect(reverse("cras:home", kwargs={"pk": directorate.pk}) + f"?year={year_val}&month={month_val}&unit={unit_name}")


class CrasDataView(CrasBaseMixin, TemplateView):
    template_name = "cras/data.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        visible_units = self.filter_units(CRAS_UNITS)
        reports = {}
        rma_data = {}
        for r in CrasReport.objects.filter(directorate=directorate, year=selected_year):
            key = (strip_accents(r.unit_name).upper(), r.month)
            if key not in reports:
                reports[key] = r
            unit_upper = strip_accents(r.unit_name).upper()
            if unit_upper not in rma_data:
                rma_data[unit_upper] = {}
            rma_data[unit_upper][r.month] = {"url": r.rma_url, "name": r.anexo_rma}
        units_tables = []
        for unit in visible_units:
            unit_key = strip_accents(unit).upper()
            groups = []
            for title, fields in CrasReportForm.section_map:
                rows = []
                for f in fields:
                    rows.append({
                        "label": CrasReportForm.labels.get(f, f), "key": f,
                        "values": [{"val": getattr(reports.get((unit_key, m)), f, "") if reports.get((unit_key, m)) else "", "sub_id": reports.get((unit_key, m)).id if reports.get((unit_key, m)) else None, "month": m, "year": selected_year, "unit": unit} for m in range(1, 13)]
                    })
                groups.append({"title": title, "rows": rows})
            rma_row = []
            for m in range(1, 13):
                rm = rma_data.get(unit_key, {}).get(m, {})
                rma_row.append(rm)
            units_tables.append({"unit": unit, "groups": groups, "rma": rma_row})
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "month_labels": [l for _, l in MONTH_LABELS],
            "units_tables": units_tables,
            "can_delete": self.is_admin(),
        })
        return context

class CrasMonthlyNarrativeView(CrasBaseMixin, TemplateView):
    template_name = "cras/monthly_report.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        month_val = self.get_month_number()

        # Agente vê só o próprio relatório; diretor/admin vêem todos da diretoria
        qs = MonthlyReport.objects.filter(directorate=directorate, setor="cras", year=selected_year, month=month_val)
        if self.is_agente():
            qs = qs.filter(user_external_id=self.request.user.pk)
        report = qs.first()

        history_qs = MonthlyReport.objects.filter(directorate=directorate, setor="cras").order_by("-year", "-month")
        if self.is_agente():
            history_qs = history_qs.filter(user_external_id=self.request.user.pk)
        history = history_qs[:8]

        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "selected_month": month_val,
            "monthly_report": report,
            "history": history,
        })
        return context

class CrasNarrativeListView(CrasBaseMixin, TemplateView):
    template_name = "cras/reports.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        selected_year = self.get_year()
        reports = MonthlyReport.objects.filter(directorate=directorate, setor="cras").order_by("-year", "-month")
        if selected_year:
            reports = reports.filter(year=selected_year)
        # Agente vê só os próprios relatórios
        if self.is_agente():
            reports = reports.filter(user_external_id=self.request.user.pk)
        context.update({
            "directorate": directorate,
            "selected_year": selected_year,
            "reports": reports,
            "can_delete": self.is_admin(),
        })
        return context

class CrasQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]
    def post(self, request):
        sub_id = request.POST.get("sub_id"); key = request.POST.get("key"); value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month")); year = int(request.POST.get("year")); unit = request.POST.get("unit")
        directorate = Directorate.objects.filter(name__icontains="CRAS").first()
        if not directorate: directorate = Directorate.objects.filter(name__icontains="Proteção Social Básica").first()
        if sub_id and sub_id != "None" and sub_id != "":
            report = get_object_or_404(CrasReport, id=sub_id)
        else:
            report, _ = CrasReport.objects.get_or_create(
                directorate=directorate, 
                month=month, 
                year=year, 
                unit_name=unit,
                defaults={'created_at': timezone.now(), 'updated_at': timezone.now()}
            )
        setattr(report, key, value)
        report.updated_at = timezone.now()
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

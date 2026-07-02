import math
import uuid
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from django.views.generic import DetailView, FormView, TemplateView, View
from apps.directorates.models import Directorate, MonthlyReport

from .forms import CreasIdosoForm, CreasPcdForm, VICTIM_PREFIXES
from .models import CreasIdosoReport, CreasPcdReport

MONTH_LABELS = [
    (1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
    (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ"),
]
MONTH_OPTIONS = [
    (1, "Janeiro"), (2, "Fevereiro"), (3, "Marco"), (4, "Abril"),
    (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
    (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro"),
]


def safe_int(val):
    return int(val or 0)


def build_sparkline(values):
    if not values or max(values) == 0:
        return ""
    width, height = 92, 34
    mx = max(values) or 1
    step = width / max(len(values) - 1, 1)
    pts = [f"{round(i*step,2)},{round(height-((v/mx)*(height-4))-2,2)}" for i, v in enumerate(values)]
    return " ".join(pts)


def build_variation(values, selected_month):
    if not values:
        return None
    if selected_month != "all":
        idx = max(0, int(selected_month) - 1)
        if idx == 0:
            return None
        curr, prev = values[idx], values[idx - 1]
    else:
        nonzero = [(i, v) for i, v in enumerate(values) if v]
        if len(nonzero) < 2:
            return None
        curr, prev = nonzero[-1][1], nonzero[-2][1]
    if not prev:
        return None
    delta = ((curr - prev) / prev) * 100
    return {"text": f"{abs(delta):.1f}%".replace(".", ","),
            "direction": "positive" if delta >= 0 else "negative",
            "icon": "trending-up" if delta >= 0 else "trending-down"}


def build_year_range(qs_list, fallback):
    years = set()
    for qs in qs_list:
        for y in qs.values_list("year", flat=True):
            years.add(y)
    ys = sorted(years, reverse=True)
    if fallback not in ys:
        ys.insert(0, fallback)
    return ys


def month_name(n):
    for m, name in MONTH_LABELS:
        if m == n:
            return name
    return str(n)


def period_label(year, month):
    return f"JAN - DEZ {year}" if month == "all" else f"{month_name(int(month))} {year}"


class CreasBaseMixin(DirectorateAccessMixin):
    def get_directorate(self):
        d = Directorate.objects.filter(pk=self.kwargs["pk"]).first()
        if not d:
            raise Http404("Diretoria nao encontrada.")
        return d

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"

    def get_month_number(self):
        m = self.request.GET.get("month")
        return int(m) if m and m != "all" else date.today().month


class CreasHomeView(TvTemplateMixin, CreasBaseMixin, DetailView):
    template_name = "creasidoso/home.html"
    tv_template_name = "creasidoso/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        directorate = self.object
        year = self.get_year()
        month = self.get_month()
        month_num = self.get_month_number()

        idoso_qs = CreasIdosoReport.objects.filter(directorate=directorate, year=year).order_by("month")
        pcd_qs = CreasPcdReport.objects.filter(directorate=directorate, year=year).order_by("month")
        idoso_by_month = {r.month: r for r in idoso_qs}
        pcd_by_month = {r.month: r for r in pcd_qs}

        years_qs = build_year_range([CreasIdosoReport.objects.filter(directorate=directorate),
                                      CreasPcdReport.objects.filter(directorate=directorate)], year)

        def get_val(qs_by_month, field):
            if month == "all":
                return sum(safe_int(qs_by_month.get(m, None) and getattr(qs_by_month[m], field, 0)) for m in range(1, 13))
            r = qs_by_month.get(int(month))
            return safe_int(getattr(r, field, 0)) if r else 0

        def get_history(qs_by_month, field):
            return [safe_int(getattr(qs_by_month.get(m, None), field, 0) if qs_by_month.get(m) else 0) for m in range(1, 13)]

        # KPI 1: Violencia Idoso
        idoso_victim_fields = [f"{p}_total" for p, _ in VICTIM_PREFIXES]
        idoso_violencia = get_val(idoso_by_month, "paefi_inseridos") + sum(get_val(idoso_by_month, f) for f in idoso_victim_fields)
        idoso_violencia_hist = get_history(idoso_by_month, "paefi_inseridos")
        for f in idoso_victim_fields:
            f_hist = get_history(idoso_by_month, f)
            idoso_violencia_hist = [idoso_violencia_hist[i] + f_hist[i] for i in range(12)]

        # KPI 2: Violencia PCD
        pcd_victim_fields = [f"def_{p}_total" for p, _ in VICTIM_PREFIXES]
        pcd_violencia = sum(get_val(pcd_by_month, f) for f in pcd_victim_fields)
        pcd_violencia_hist = []
        for i in range(12):
            total = 0
            for f in pcd_victim_fields:
                total += get_history(pcd_by_month, f)[i]
            pcd_violencia_hist.append(total)

        # KPI 3: Familias Acomp.
        familias = get_val(idoso_by_month, "paefi_acomp_inicio") + get_val(idoso_by_month, "paefi_inseridos")
        familias_hist = [a + b for a, b in zip(get_history(idoso_by_month, "paefi_acomp_inicio"),
                                                get_history(idoso_by_month, "paefi_inseridos"))]

        cards = [
            {"label": f"Violencia Idoso ({month_name(month_num) if month != 'all' else 'Ano'})",
             "value": idoso_violencia, "sparkline": build_sparkline(idoso_violencia_hist),
             "icon": "heart-pulse", "color": "#0ea5e9",
             "variation": build_variation(idoso_violencia_hist, month)},
            {"label": f"Violencia PCD ({month_name(month_num) if month != 'all' else 'Ano'})",
             "value": pcd_violencia, "sparkline": build_sparkline(pcd_violencia_hist),
             "icon": "accessibility", "color": "#f59e0b",
             "variation": build_variation(pcd_violencia_hist, month)},
            {"label": f"Familias Acomp. ({month_name(month_num) if month != 'all' else 'Ano'})",
             "value": familias, "sparkline": build_sparkline(familias_hist),
             "icon": "users", "color": "#10b981",
             "variation": build_variation(familias_hist, month)},
        ]

        # Donut 1: Idoso slices
        donut_idoso_labels = ["Negligencia/Abandono", "Violencia Fisica/Psic.", "Exploracao Financeira",
                               "Abuso Sexual", "Exploracao Sexual"]
        donut_idoso_fields = ["negligencia_total", "violencia_fisica_total", "exploracao_financeira_total",
                              "abuso_sexual_total", "exploracao_sexual_total"]
        donut_idoso_data = [get_val(idoso_by_month, f) for f in donut_idoso_fields]
        donut_colors = ["#3b82f6", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6"]
        donut_idoso_items = [{"label": l, "value": v, "color": c} for l, v, c in zip(donut_idoso_labels, donut_idoso_data, donut_colors) if v > 0]

        # Donut 2: PCD slices
        donut_pcd_fields = [f"def_{f}" for f in donut_idoso_fields]
        donut_pcd_data = [get_val(pcd_by_month, f) for f in donut_pcd_fields]
        donut_pcd_items = [{"label": l, "value": v, "color": c} for l, v, c in zip(donut_idoso_labels, donut_pcd_data, donut_colors) if v > 0]

        # Bar 1: Idoso bars
        bar_idoso_items = [
            {"label": "Violencia Fis/Psic", "value": get_val(idoso_by_month, "violencia_fisica_total")},
            {"label": "Negligencia/Abandono", "value": get_val(idoso_by_month, "negligencia_total")},
            {"label": "Exploracao Financeira", "value": get_val(idoso_by_month, "exploracao_financeira_total")},
            {"label": "Abuso/Expl. Sexual", "value": get_val(idoso_by_month, "abuso_sexual_total") + get_val(idoso_by_month, "exploracao_sexual_total")},
        ]

        # Bar 2: PCD bars
        bar_pcd_items = [
            {"label": "Violencia Fis/Psic", "value": get_val(pcd_by_month, "def_violencia_fisica_total")},
            {"label": "Negligencia/Abandono", "value": get_val(pcd_by_month, "def_negligencia_total")},
            {"label": "Exploracao Financeira", "value": get_val(pcd_by_month, "def_exploracao_financeira_total")},
            {"label": "Abuso/Expl. Sexual", "value": get_val(pcd_by_month, "def_abuso_sexual_total") + get_val(pcd_by_month, "def_exploracao_sexual_total")},
        ]

        ctx.update({
            "selected_year": year, "selected_month": month,
            "months_range": MONTH_OPTIONS, "years_range": years_qs,
            "cards": cards,
            "donut_idoso_items": donut_idoso_items,
            "donut_pcd_items": donut_pcd_items,
            "donut_colors": donut_colors,
            "bar_idoso_items": bar_idoso_items,
            "bar_pcd_items": bar_pcd_items,
            "period_label": period_label(year, month),
        })
        return ctx


class CreasIdosoFormView(CreasBaseMixin, FormView):
    template_name = "creasidoso/form.html"
    form_class = CreasIdosoForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = CreasIdosoReport.objects.filter(
            directorate=self.get_directorate(), month=self.get_month_number(), year=self.get_year()
        ).first()
        if r:
            for f in self.form_class.Meta.model._meta.fields:
                if f.name in self.form_class.base_fields:
                    initial[f.name] = getattr(r, f.name)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]
        items = [{"title": t, "fields": [form[f] for f in fs]} for t, fs in self.form_class.section_map]
        ctx.update({"directorate": self.get_directorate(), "section_items": items,
                     "subcategory": "idoso", "selected_year": self.get_year(), "selected_month": self.get_month_number()})
        return ctx

    def form_valid(self, form):
        d = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        try:
            r = CreasIdosoReport.objects.get(directorate=d, month=month_val, year=year_val)
        except CreasIdosoReport.DoesNotExist:
            from django.db import connection
            c = connection.cursor()
            c.execute("SELECT id FROM auth.users LIMIT 1")
            row = c.fetchone()
            fb_user = row[0] if row else uuid.uuid4()
            r = CreasIdosoReport(directorate=d, month=month_val, year=year_val, created_by=fb_user, created_at=datetime.now())
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = datetime.now()
        r.save()
        messages.success(self.request, "Dados CREAS Idoso salvos.")
        return redirect(reverse("creasidoso:home", kwargs={"pk": d.pk}) + f"?year={year_val}")


class CreasPcdFormView(CreasBaseMixin, FormView):
    template_name = "creasidoso/form.html"
    form_class = CreasPcdForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = CreasPcdReport.objects.filter(
            directorate=self.get_directorate(), month=self.get_month_number(), year=self.get_year()
        ).first()
        if r:
            for f in self.form_class.Meta.model._meta.fields:
                if f.name in self.form_class.base_fields:
                    initial[f.name] = getattr(r, f.name)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]
        items = [{"title": t, "fields": [form[f] for f in fs]} for t, fs in self.form_class.section_map]
        ctx.update({"directorate": self.get_directorate(), "section_items": items,
                     "subcategory": "pcd", "selected_year": self.get_year(), "selected_month": self.get_month_number()})
        return ctx

    def form_valid(self, form):
        d = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        try:
            r = CreasPcdReport.objects.get(directorate=d, month=month_val, year=year_val)
        except CreasPcdReport.DoesNotExist:
            from django.db import connection
            c = connection.cursor()
            c.execute("SELECT id FROM auth.users LIMIT 1")
            row = c.fetchone()
            fb_user = row[0] if row else uuid.uuid4()
            r = CreasPcdReport(directorate=d, month=month_val, year=year_val, created_by=fb_user, created_at=datetime.now())
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = datetime.now()
        r.save()
        messages.success(self.request, "Dados CREAS PCD salvos.")
        return redirect(reverse("creasidoso:home", kwargs={"pk": d.pk}) + f"?year={year_val}")


class CreasIdosoDataView(CreasBaseMixin, TemplateView):
    template_name = "creasidoso/data.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasIdosoReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        for title, fields in CreasIdosoForm.section_map:
            rows = [{"label": CreasIdosoForm.labels.get(f, f),
                     "key": f,
                     "values": [{"val": getattr(by_month.get(m, None), f, "") if by_month.get(m) else "",
                                 "sub_id": by_month.get(m).id if by_month.get(m) else None,
                                 "month": m,
                                 "year": year}
                                for m in range(1, 13)]}
                    for f in fields]
            groups.append({"title": title, "rows": rows})
        ctx.update({"directorate": d, "selected_year": year, "subcategory": "idoso",
                     "month_labels": [l for _, l in MONTH_LABELS], "table_groups": groups,
                     "can_delete": self.is_admin()})
        return ctx


class CreasPcdDataView(CreasBaseMixin, TemplateView):
    template_name = "creasidoso/data.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasPcdReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        for title, fields in CreasPcdForm.section_map:
            rows = [{"label": CreasPcdForm.labels.get(f, f),
                     "key": f,
                     "values": [{"val": getattr(by_month.get(m, None), f, "") if by_month.get(m) else "",
                                 "sub_id": by_month.get(m).id if by_month.get(m) else None,
                                 "month": m,
                                 "year": year}
                                for m in range(1, 13)]}
                    for f in fields]
            groups.append({"title": title, "rows": rows})
        ctx.update({"directorate": d, "selected_year": year, "subcategory": "pcd",
                     "month_labels": [l for _, l in MONTH_LABELS], "table_groups": groups,
                     "can_delete": self.is_admin()})
        return ctx


class CreasMonthlyNarrativeView(CreasBaseMixin, TemplateView):
    template_name = "creasidoso/monthly_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        m = self.get_month_number()
        qs = MonthlyReport.objects.filter(directorate=d, setor="creas", year=year, month=m)
        if self.is_agente():
            qs = qs.filter(user_external_id=self.request.user.pk)
        r = qs.first()
        history_qs = MonthlyReport.objects.filter(directorate=d, setor="creas").order_by("-year", "-month")
        if self.is_agente():
            history_qs = history_qs.filter(user_external_id=self.request.user.pk)
        history = history_qs[:8]
        ctx.update({"directorate": d, "selected_year": year, "selected_month": m, "monthly_report": r, "history": history})
        return ctx


class CreasNarrativeListView(CreasBaseMixin, TemplateView):
    template_name = "creasidoso/reports.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = MonthlyReport.objects.filter(directorate=d, setor="creas").order_by("-year", "-month")
        if year:
            reports = reports.filter(year=year)
        if self.is_agente():
            reports = reports.filter(user_external_id=self.request.user.pk)
        ctx.update({"directorate": d, "selected_year": year, "reports": reports, "can_delete": self.is_admin()})
        return ctx

class CreasSharedQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]
    model = None

    def post(self, request):
        sub_id = request.POST.get("sub_id")
        key = request.POST.get("key")
        value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        
        # Tenta encontrar a diretoria pelo nome de forma robusta
        directorate = Directorate.objects.filter(name__icontains="CREAS").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="Proteção Social Especial").first()
        
        if sub_id and sub_id != "None" and sub_id != "":
            from django.shortcuts import get_object_or_404
            report = get_object_or_404(self.model, id=sub_id)
        else:
            report, _ = self.model.objects.get_or_create(
                directorate=directorate,
                month=month,
                year=year
            )

        setattr(report, key, value)
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

class CreasIdosoQuickEditView(CreasSharedQuickEditView):
    model = CreasIdosoReport

class CreasPcdQuickEditView(CreasSharedQuickEditView):
    model = CreasPcdReport

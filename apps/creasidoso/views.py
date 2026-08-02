import math
import uuid
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin, NarrativeReportMixin, NarrativeEditorMixin
from apps.core.export import ExcelExportMixin, build_workbook
from django.views.generic import DetailView, FormView, TemplateView, View
from apps.core.export import ExcelExportMixin, build_workbook
from apps.core.notifications import log_activity
from apps.core.utils import build_period_label, MONTH_OPTIONS
from apps.directorates.models import Directorate, MonthlyReport

from .forms import CreasIdosoForm, CreasPcdForm, IDOSO_VIOLATION_PREFIXES, IDOSO_SUFFIXES, PCD_VIOLATION_PREFIXES, PCD_SUFFIXES
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

        # KPI 1: Violencia Idoso (soma masc+fem de todos os totais)
        idoso_victim_fields = [f"{p}_total_{g}" for p, _ in IDOSO_VIOLATION_PREFIXES for g in ["masc", "fem"]]
        idoso_violencia = get_val(idoso_by_month, "paefi_inseridos") + sum(get_val(idoso_by_month, f) for f in idoso_victim_fields)
        idoso_violencia_hist = get_history(idoso_by_month, "paefi_inseridos")
        for f in idoso_victim_fields:
            f_hist = get_history(idoso_by_month, f)
            idoso_violencia_hist = [idoso_violencia_hist[i] + f_hist[i] for i in range(12)]

        # KPI 2: Violencia PCD (soma masc+fem de todos os totais)
        pcd_victim_fields = [f"def_{p}_total_{g}" for p, _ in PCD_VIOLATION_PREFIXES for g in ["masc", "fem"]]
        pcd_violencia = sum(get_val(pcd_by_month, f) for f in pcd_victim_fields)
        pcd_violencia_hist = [0] * 12
        for f in pcd_victim_fields:
            f_hist = get_history(pcd_by_month, f)
            pcd_violencia_hist = [pcd_violencia_hist[i] + f_hist[i] for i in range(12)]

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

        # Donut 1: Idoso slices (soma masc+fem)
        donut_idoso_labels = ["Negligencia/Abandono", "Violencia Fisica/Psic.", "Exploracao Financeira",
                               "Abuso Sexual", "Exploracao Sexual"]
        donut_idoso_base = ["negligencia_total", "violencia_fisica_total", "exploracao_financeira_total",
                            "abuso_sexual_total", "exploracao_sexual_total"]
        donut_idoso_data = []
        for f in donut_idoso_base:
            donut_idoso_data.append(get_val(idoso_by_month, f"{f}_masc") + get_val(idoso_by_month, f"{f}_fem"))
        donut_colors = ["#3b82f6", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6"]
        donut_idoso_items = [{"label": l, "value": v, "color": c} for l, v, c in zip(donut_idoso_labels, donut_idoso_data, donut_colors) if v > 0]

        # Donut 2: PCD slices (soma masc+fem)
        donut_pcd_fields_flat = [f"def_{f}_total" for f in donut_idoso_base]
        donut_pcd_data = []
        for f in donut_pcd_fields_flat:
            donut_pcd_data.append(get_val(pcd_by_month, f"{f}_masc") + get_val(pcd_by_month, f"{f}_fem"))
        donut_pcd_items = [{"label": l, "value": v, "color": c} for l, v, c in zip(donut_idoso_labels, donut_pcd_data, donut_colors) if v > 0]

        # Bar 1: Idoso bars (soma masc+fem)
        def idoso_bar_val(field):
            return get_val(idoso_by_month, f"{field}_masc") + get_val(idoso_by_month, f"{field}_fem")

        bar_idoso_items = [
            {"label": "Violencia Fis/Psic", "value": idoso_bar_val("violencia_fisica_total")},
            {"label": "Negligencia/Abandono", "value": idoso_bar_val("negligencia_total")},
            {"label": "Exploracao Financeira", "value": idoso_bar_val("exploracao_financeira_total")},
            {"label": "Abuso/Expl. Sexual", "value": idoso_bar_val("abuso_sexual_total") + idoso_bar_val("exploracao_sexual_total")},
        ]

        # Bar 2: PCD bars (soma masc+fem)
        def pcd_bar_val(field):
            return get_val(pcd_by_month, f"{field}_masc") + get_val(pcd_by_month, f"{field}_fem")

        bar_pcd_items = [
            {"label": "Violencia Fis/Psic", "value": pcd_bar_val("def_violencia_fisica_total")},
            {"label": "Negligencia/Abandono", "value": pcd_bar_val("def_negligencia_total")},
            {"label": "Exploracao Financeira", "value": pcd_bar_val("def_exploracao_financeira_total")},
            {"label": "Abuso/Expl. Sexual", "value": pcd_bar_val("def_abuso_sexual_total") + pcd_bar_val("def_exploracao_sexual_total")},
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
        r = self._get_existing_report()
        if r:
            for f in self.form_class.Meta.model._meta.fields:
                if f.name in self.form_class.base_fields:
                    initial[f.name] = getattr(r, f.name)
        return initial

    def _get_existing_report(self):
        return CreasIdosoReport.objects.filter(
            directorate=self.get_directorate(), month=self.get_month_number(), year=self.get_year()
        ).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]
        items = [{"title": t, "fields": [form[f] for f in fs]} for t, fs in form.section_map]
        existing_report = self._get_existing_report()
        ctx.update({"directorate": self.get_directorate(), "section_items": items,
                     "subcategory": "idoso", "selected_year": self.get_year(), "selected_month": self.get_month_number(),
                     "is_locked": bool(existing_report), "is_admin_user": self.is_admin(),
                     "month_options": MONTH_OPTIONS})
        return ctx

    def post(self, request, *args, **kwargs):
        if self._get_existing_report():
            messages.error(
                request,
                "Este mês já foi lançado. Peça a um administrador para reabrir antes de preencher novamente.",
            )
            directorate = self.get_directorate()
            return redirect(
                reverse("creasidoso:form-idoso", kwargs={"pk": directorate.pk})
                + f"?year={self.get_year()}&month={self.get_month_number()}"
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        d = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        try:
            r = CreasIdosoReport.objects.get(directorate=d, month=month_val, year=year_val)
        except CreasIdosoReport.DoesNotExist:
            fb_user = self.request.user.id
            r = CreasIdosoReport(directorate=d, month=month_val, year=year_val, created_by=fb_user, created_at=timezone.now())
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = timezone.now()
        r.save()
        messages.success(self.request, "Dados CREAS Idoso salvos.")
        log_activity(self.request, d, "created", "report",
                     f"CREAS Idoso — {build_period_label(year_val, month_val)}",
                     url=reverse("creasidoso:data-idoso", kwargs={"pk": d.pk}) + f"?year={year_val}")
        return redirect(reverse("creasidoso:home", kwargs={"pk": d.pk}) + f"?year={year_val}")


class CreasPcdFormView(CreasBaseMixin, FormView):
    template_name = "creasidoso/form.html"
    form_class = CreasPcdForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = self._get_existing_report()
        if r:
            for f in self.form_class.Meta.model._meta.fields:
                if f.name in self.form_class.base_fields:
                    initial[f.name] = getattr(r, f.name)
        return initial

    def _get_existing_report(self):
        return CreasPcdReport.objects.filter(
            directorate=self.get_directorate(), month=self.get_month_number(), year=self.get_year()
        ).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]
        items = [{"title": t, "fields": [form[f] for f in fs]} for t, fs in form.section_map]
        existing_report = self._get_existing_report()
        ctx.update({"directorate": self.get_directorate(), "section_items": items,
                     "subcategory": "pcd", "selected_year": self.get_year(), "selected_month": self.get_month_number(),
                     "is_locked": bool(existing_report), "is_admin_user": self.is_admin(),
                     "month_options": MONTH_OPTIONS})
        return ctx

    def post(self, request, *args, **kwargs):
        if self._get_existing_report():
            messages.error(
                request,
                "Este mês já foi lançado. Peça a um administrador para reabrir antes de preencher novamente.",
            )
            directorate = self.get_directorate()
            return redirect(
                reverse("creasidoso:form-pcd", kwargs={"pk": directorate.pk})
                + f"?year={self.get_year()}&month={self.get_month_number()}"
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        d = self.get_directorate()
        month_val = form.cleaned_data["month"]
        year_val = form.cleaned_data["year"]
        try:
            r = CreasPcdReport.objects.get(directorate=d, month=month_val, year=year_val)
        except CreasPcdReport.DoesNotExist:
            fb_user = self.request.user.id
            r = CreasPcdReport(directorate=d, month=month_val, year=year_val, created_by=fb_user, created_at=timezone.now())
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = timezone.now()
        r.save()
        messages.success(self.request, "Dados CREAS PCD salvos.")
        log_activity(self.request, d, "created", "report",
                     f"CREAS PCD — {build_period_label(year_val, month_val)}",
                     url=reverse("creasidoso:data-pcd", kwargs={"pk": d.pk}) + f"?year={year_val}")
        return redirect(reverse("creasidoso:home", kwargs={"pk": d.pk}) + f"?year={year_val}")


class CreasIdosoDataView(ExcelExportMixin, CreasBaseMixin, TemplateView):
    template_name = "creasidoso/data.html"
    export_filename = "creas_idoso_dados.xlsx"

    def export_excel(self):
        ctx = self.get_context_data()
        sheets = []
        for group in ctx["table_groups"]:
            sheets.append({
                "title": group["title"],
                "headers": [l for _, l in MONTH_LABELS],
                "rows": [
                    [row["label"]] + [v["val"] for v in row["values"]]
                    for row in group["rows"]
                ],
            })
        return build_workbook(sheets, self.export_filename)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasIdosoReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}

        # Build section_map and labels (matches CreasIdosoForm.__init__)
        idoso_section_map = [
            (
                "Famílias em acompanhamento no PAEFI",
                ["paefi_acomp_inicio", "paefi_inseridos", "paefi_desligados",
                 "paefi_total_acompanhamento", "paefi_bolsa_familia", "paefi_bpc", "paefi_substancias"],
            )
        ]
        for pref, label in IDOSO_VIOLATION_PREFIXES:
            fields = []
            for suf, _suf_label in IDOSO_SUFFIXES:
                fields.append(f"{pref}_{suf}_masc")
                fields.append(f"{pref}_{suf}_fem")
            fields.append(f"{pref}_total_geral")
            idoso_section_map.append((label, fields))

        idoso_labels = {
            "paefi_acomp_inicio": "Famílias em Acomp. 1º Dia Mês",
            "paefi_inseridos": "Famílias inseridas",
            "paefi_desligados": "Famílias desligadas",
            "paefi_total_acompanhamento": "Total de famílias em acompanhamento",
            "paefi_bolsa_familia": "Famílias benef. Bolsa Família",
            "paefi_bpc": "Famílias com BPC",
            "paefi_substancias": "Famílias com dep. Substâncias psicoativas",
        }
        for pref, label in IDOSO_VIOLATION_PREFIXES:
            for suf, suf_label in IDOSO_SUFFIXES:
                idoso_labels[f"{pref}_{suf}_masc"] = f"{suf_label} — Masculino"
                idoso_labels[f"{pref}_{suf}_fem"] = f"{suf_label} — Feminino"
            idoso_labels[f"{pref}_total_geral"] = "Total Geral"

        groups = []
        for title, fields in idoso_section_map:
            rows = [{"label": idoso_labels.get(f, f),
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


class CreasPcdDataView(ExcelExportMixin, CreasBaseMixin, TemplateView):
    template_name = "creasidoso/data.html"
    export_filename = "creas_pcd_dados.xlsx"

    def export_excel(self):
        ctx = self.get_context_data()
        sheets = []
        for group in ctx["table_groups"]:
            sheets.append({
                "title": group["title"],
                "headers": [l for _, l in MONTH_LABELS],
                "rows": [
                    [row["label"]] + [v["val"] for v in row["values"]]
                    for row in group["rows"]
                ],
            })
        return build_workbook(sheets, self.export_filename)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasPcdReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        # Build section_map and labels from constants (matches what CreasPcdForm builds in __init__)
        pcd_section_map = []
        pcd_labels = {}
        for pref, label in PCD_VIOLATION_PREFIXES:
            fields = []
            for suf, suf_label in PCD_SUFFIXES:
                fields.append(f"def_{pref}_{suf}_masc")
                fields.append(f"def_{pref}_{suf}_fem")
            pcd_section_map.append((f"{label} (Pessoa com Deficiência)", fields))
        for pref, label in PCD_VIOLATION_PREFIXES:
            for suf, suf_label in PCD_SUFFIXES:
                pcd_labels[f"def_{pref}_{suf}_masc"] = f"{suf_label} (Masculino)"
                pcd_labels[f"def_{pref}_{suf}_fem"] = f"{suf_label} (Feminino)"

        for title, fields in pcd_section_map:
            rows = [{"label": pcd_labels.get(f, f),
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


class CreasMonthlyNarrativeView(CreasBaseMixin, NarrativeReportMixin, RoleRequiredMixin, TemplateView):
    template_name = "directorates/shared/narrative_report.html"
    setor = "creas"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_editor_url(self, month, year):
        d = self.get_directorate()
        return f"{reverse('creasidoso:narrative-editor', kwargs={'pk': d.pk})}?year={year}&month={month}"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        m = self.get_month_number()
        hist_year = int(self.request.GET.get("hist_year") or year)
        ctx.update(self.get_narrative_context(m, year, hist_year))
        ctx.update({
            "report_label": "CREAS Idoso e Pessoa com Deficiência",
            "theme_class": "theme-amber",
            "back_url": reverse("creasidoso:home", kwargs={"pk": d.pk}) + f"?year={year}",
        })
        return ctx


class CreasNarrativeEditorView(CreasBaseMixin, NarrativeEditorMixin, RoleRequiredMixin, TemplateView):
    template_name = "directorates/shared/narrative_editor.html"
    setor = "creas"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_view_url(self, month, year):
        d = self.get_directorate()
        return f"{reverse('creasidoso:monthly-report', kwargs={'pk': d.pk})}?year={year}&month={month}"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = self.get_year()
        m = self.get_month_number()
        ctx.update(self.get_editor_context(m, year))
        ctx.update({
            "report_label": "CREAS Idoso e Pessoa com Deficiência",
            "theme_class": "theme-amber",
            "months_range": MONTH_OPTIONS,
            "cancel_url": self.get_view_url(m, year),
        })
        return ctx

    def post(self, request, *args, **kwargs):
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        directorate = self.save_narrative(request, month, year)
        if directorate is not None:
            log_activity(request, directorate, "finalized", "report",
                         f"Relatorio Mensal CREAS Idoso e PCD {build_period_label(year, month)}",
                         url=self.get_view_url(month, year))
        return redirect(self.get_view_url(month, year))

class CreasIdosoDeleteMonthView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request, *args, **kwargs):
        month = request.POST.get("month")
        year = request.POST.get("year")
        deleted, _ = CreasIdosoReport.objects.filter(
            directorate_id=kwargs["pk"], month=month, year=year
        ).delete()
        return JsonResponse({"status": "success", "deleted": deleted})


class CreasPcdDeleteMonthView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request, *args, **kwargs):
        month = request.POST.get("month")
        year = request.POST.get("year")
        deleted, _ = CreasPcdReport.objects.filter(
            directorate_id=kwargs["pk"], month=month, year=year
        ).delete()
        return JsonResponse({"status": "success", "deleted": deleted})


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
        
        NUMERIC_TYPES = ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'FloatField', 'DecimalField')
        allowed_keys = {f.name for f in self.model._meta.get_fields()
                        if hasattr(f, 'get_internal_type') and f.get_internal_type() in NUMERIC_TYPES}
        if key not in allowed_keys:
            return JsonResponse({"error": "Campo não permitido"}, status=400)

        if sub_id and sub_id != "None" and sub_id != "":
            from django.shortcuts import get_object_or_404
            report = get_object_or_404(self.model, id=sub_id)
        else:
            report, _ = self.model.objects.get_or_create(
                directorate=directorate,
                month=month,
                year=year,
                defaults={
                    "created_by": request.user.id,
                    "created_at": timezone.now(),
                    "updated_at": timezone.now(),
                },
            )

        setattr(report, key, value)
        report.updated_at = timezone.now()
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

class CreasIdosoQuickEditView(CreasSharedQuickEditView):
    model = CreasIdosoReport

class CreasPcdQuickEditView(CreasSharedQuickEditView):
    model = CreasPcdReport

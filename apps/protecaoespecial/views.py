import uuid
from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from apps.directorates.models import Directorate

from .models import CreasProtetivoReport, CreasSocioeducativoReport
from .forms import CreasProtetivoForm, CreasSocioeducativoForm

MONTH_LABELS = [
    (1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
    (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ"),
]

MONTH_OPTIONS = [
    (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
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
    pts = [f"{round(i*step, 2)},{round(height-((v/mx)*(height-4))-2, 2)}" for i, v in enumerate(values)]
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
    return {
        "text": f"{abs(delta):.1f}%".replace(".", ","),
        "direction": "positive" if delta >= 0 else "negative",
        "icon": "trending-up" if delta >= 0 else "trending-down"
    }


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


class ProteacaoEspecialBaseMixin(DirectorateAccessMixin):
    def get_directorate(self):
        d = Directorate.objects.filter(pk=self.kwargs["pk"]).first()
        if not d:
            raise Http404("Diretoria não encontrada.")
        return d

    def get_year(self):
        return int(self.request.GET.get("year") or date.today().year)

    def get_month(self):
        return self.request.GET.get("month") or "all"

    def get_month_number(self):
        m = self.request.GET.get("month")
        return int(m) if m and m != "all" else date.today().month


class ProtecaoEspecialHomeView(TvTemplateMixin, ProteacaoEspecialBaseMixin, DetailView):
    template_name = "protecaoespecial/home.html"
    tv_template_name = "protecaoespecial/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        directorate = self.object
        year = self.get_year()
        month = self.get_month()
        month_num = self.get_month_number()

        protetivo_qs = CreasProtetivoReport.objects.filter(directorate=directorate, year=year).order_by("month")
        socio_qs = CreasSocioeducativoReport.objects.filter(directorate=directorate, year=year).order_by("month")
        
        protetivo_by_month = {r.month: r for r in protetivo_qs}
        socio_by_month = {r.month: r for r in socio_qs}

        years_qs = build_year_range([
            CreasProtetivoReport.objects.filter(directorate=directorate),
            CreasSocioeducativoReport.objects.filter(directorate=directorate)
        ], year)

        def get_val(qs_by_month, field):
            if month == "all":
                return sum(safe_int(qs_by_month.get(m, None) and getattr(qs_by_month[m], field, 0)) for m in range(1, 13))
            r = qs_by_month.get(int(month))
            return safe_int(getattr(r, field, 0)) if r else 0

        def get_history(qs_by_month, field):
            return [safe_int(getattr(qs_by_month.get(m, None), field, 0) if qs_by_month.get(m) else 0) for m in range(1, 13)]

        # KPI 1: Famílias Protetivo (Current active or latest non-zero in case of all, or the selected month's value)
        fam_protetivo_hist = get_history(protetivo_by_month, "fam_atual")
        if month == "all":
            # Show latest active families or latest non-zero
            nonzero_protetivo = [v for v in fam_protetivo_hist if v > 0]
            fam_protetivo = nonzero_protetivo[-1] if nonzero_protetivo else 0
        else:
            fam_protetivo = get_val(protetivo_by_month, "fam_atual")

        # KPI 2: Famílias Socioeducativo
        fam_socio_hist = get_history(socio_by_month, "fam_total_acompanhamento")
        if month == "all":
            nonzero_socio = [v for v in fam_socio_hist if v > 0]
            fam_socio = nonzero_socio[-1] if nonzero_socio else 0
        else:
            fam_socio = get_val(socio_by_month, "fam_total_acompanhamento")

        # KPI 3: Adolescentes Socioeducativo (Total Masculino + Total Feminino em acompanhamento)
        masc_socio_hist = get_history(socio_by_month, "masc_total_parcial")
        fem_socio_hist = get_history(socio_by_month, "fem_total_parcial")
        adolescentes_hist = [m + f for m, f in zip(masc_socio_hist, fem_socio_hist)]
        if month == "all":
            nonzero_adolescentes = [v for v in adolescentes_hist if v > 0]
            adolescentes = nonzero_adolescentes[-1] if nonzero_adolescentes else 0
        else:
            adolescentes = get_val(socio_by_month, "masc_total_parcial") + get_val(socio_by_month, "fem_total_parcial")

        cards = [
            {
                "label": f"Famílias Protetivo ({month_name(month_num) if month != 'all' else 'Atual'})",
                "value": fam_protetivo, "sparkline": build_sparkline(fam_protetivo_hist),
                "icon": "home", "color": "#0ea5e9",
                "variation": build_variation(fam_protetivo_hist, month)
            },
            {
                "label": f"Famílias Socioeducativo ({month_name(month_num) if month != 'all' else 'Atual'})",
                "value": fam_socio, "sparkline": build_sparkline(fam_socio_hist),
                "icon": "users", "color": "#10b981",
                "variation": build_variation(fam_socio_hist, month)
            },
            {
                "label": f"Adolescentes Socioeducativo ({month_name(month_num) if month != 'all' else 'Atual'})",
                "value": adolescentes, "sparkline": build_sparkline(adolescentes_hist),
                "icon": "accessibility", "color": "#f59e0b",
                "variation": build_variation(adolescentes_hist, month)
            },
        ]

        # Doughnut 1: Rights Violations Categories
        violation_types = [
            ("Violência Física/Psic.", ["viol_fis_psic_masc", "viol_fis_psic_fem"]),
            ("Abuso Sexual", ["abuso_sexual_masc", "abuso_sexual_fem"]),
            ("Exploração Sexual", ["expl_sexual_masc", "expl_sexual_fem"]),
            ("Negligência/Abandono", ["negli_aband_masc", "negli_aband_fem"]),
            ("Trabalho Infantil", ["trab_infantil_masc", "trab_infantil_fem"]),
        ]
        donut_colors = ["#3b82f6", "#ef4444", "#8b5cf6", "#f59e0b", "#10b981"]
        donut_protetivo_items = []
        for (label, fields), color in zip(violation_types, donut_colors):
            total_val = sum(get_val(protetivo_by_month, f) for f in fields)
            if total_val > 0:
                donut_protetivo_items.append({"label": label, "value": total_val, "color": color})

        # Doughnut 2: Socioeducativo measures in progress (LA vs PSC)
        la_masc_total = get_val(socio_by_month, "med_masc_la_total_parcial")
        la_fem_total = get_val(socio_by_month, "med_fem_la_total_parcial")
        psc_masc_total = get_val(socio_by_month, "med_masc_psc_total_parcial")
        psc_fem_total = get_val(socio_by_month, "med_fem_psc_total_parcial")
        
        la_total = la_masc_total + la_fem_total
        psc_total = psc_masc_total + psc_fem_total
        
        donut_socio_items = []
        if la_total > 0:
            donut_socio_items.append({"label": "Liberdade Assistida (LA)", "value": la_total, "color": "#3b82f6"})
        if psc_total > 0:
            donut_socio_items.append({"label": "Prest. Serviço Comunidade (PSC)", "value": psc_total, "color": "#10b981"})

        # Bar 1: Violations by Gender
        masc_violations = sum(get_val(protetivo_by_month, f) for label, fields in violation_types for f in fields if f.endswith("_masc"))
        fem_violations = sum(get_val(protetivo_by_month, f) for label, fields in violation_types for f in fields if f.endswith("_fem"))
        bar_protetivo_items = [
            {"label": "Masculino", "value": masc_violations, "color": "#3b82f6"},
            {"label": "Feminino", "value": fem_violations, "color": "#f43f5e"},
        ]

        # Bar 2: Measures in Progress by Gender
        masc_measures = la_masc_total + psc_masc_total
        fem_measures = la_fem_total + psc_fem_total
        bar_socio_items = [
            {"label": "Masculino", "value": masc_measures, "color": "#3b82f6"},
            {"label": "Feminino", "value": fem_measures, "color": "#f43f5e"},
        ]

        ctx.update({
            "selected_year": year, "selected_month": month,
            "months_range": MONTH_OPTIONS, "years_range": years_qs,
            "cards": cards,
            "donut_protetivo_items": donut_protetivo_items,
            "donut_socio_items": donut_socio_items,
            "bar_protetivo_items": bar_protetivo_items,
            "bar_socio_items": bar_socio_items,
            "period_label": period_label(year, month),
        })
        return ctx


class CreasProtetivoFormView(ProteacaoEspecialBaseMixin, FormView):
    template_name = "protecaoespecial/form.html"
    form_class = CreasProtetivoForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = CreasProtetivoReport.objects.filter(
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
        ctx.update({
            "directorate": self.get_directorate(), "section_items": items,
            "subcategory": "protetivo", "selected_year": self.get_year(), "selected_month": self.get_month_number()
        })
        return ctx

    def form_valid(self, form):
        d = self.get_directorate()
        r, created = CreasProtetivoReport.objects.get_or_create(
            directorate=d, month=form.cleaned_data["month"], year=form.cleaned_data["year"],
        )
        if created:
            r.created_at = datetime.now()
            
        try:
            r.user_id = self.request.user.pk
        except Exception:
            pass
            
        r.created_by = self.request.user.email or self.request.user.username
        
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = datetime.now()
        r.save()
        messages.success(self.request, "Dados CREAS Protetivo salvos com sucesso.")
        return redirect(reverse("protecaoespecial:home", kwargs={"pk": d.pk}) + f"?year={form.cleaned_data['year']}")


class CreasSocioeducativoFormView(ProteacaoEspecialBaseMixin, FormView):
    template_name = "protecaoespecial/form.html"
    form_class = CreasSocioeducativoForm

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = CreasSocioeducativoReport.objects.filter(
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
        ctx.update({
            "directorate": self.get_directorate(), "section_items": items,
            "subcategory": "socioeducativo", "selected_year": self.get_year(), "selected_month": self.get_month_number()
        })
        return ctx

    def form_valid(self, form):
        d = self.get_directorate()
        r, created = CreasSocioeducativoReport.objects.get_or_create(
            directorate=d, month=form.cleaned_data["month"], year=form.cleaned_data["year"],
        )
        if created:
            r.created_at = datetime.now()
            
        try:
            r.user_id = self.request.user.pk
        except Exception:
            pass
            
        r.created_by = self.request.user.email or self.request.user.username
        
        for k, v in form.cleaned_data.items():
            setattr(r, k, v)
        r.updated_at = datetime.now()
        r.save()
        messages.success(self.request, "Dados CREAS Socioeducativo salvos com sucesso.")
        return redirect(reverse("protecaoespecial:home", kwargs={"pk": d.pk}) + f"?year={form.cleaned_data['year']}")


class CreasProtetivoDataView(ProteacaoEspecialBaseMixin, TemplateView):
    template_name = "protecaoespecial/data.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasProtetivoReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        for title, fields in CreasProtetivoForm.section_map:
            rows = [{"label": CreasProtetivoForm.labels.get(f, f),
                     "key": f,
                     "is_readonly": f in {"fam_atual", "atend_atual"},
                     "values": [{"val": getattr(by_month.get(m, None), f, "") if by_month.get(m) else "",
                                 "sub_id": by_month.get(m).id if by_month.get(m) else None,
                                 "month": m,
                                 "year": year}
                                for m in range(1, 13)]}
                    for f in fields]
            groups.append({"title": title, "rows": rows})
        ctx.update({
            "directorate": d, "selected_year": year, "subcategory": "protetivo",
            "month_labels": [l for _, l in MONTH_LABELS], "table_groups": groups,
            "can_delete": self.is_admin(),
        })
        return ctx


class CreasSocioeducativoDataView(ProteacaoEspecialBaseMixin, TemplateView):
    template_name = "protecaoespecial/data.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = CreasSocioeducativoReport.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        for title, fields in CreasSocioeducativoForm.section_map:
            rows = [{"label": CreasSocioeducativoForm.labels.get(f, f),
                     "key": f,
                     "is_readonly": f.endswith("_total_parcial") or f.endswith("_geral") or f == "fam_total_acompanhamento",
                     "values": [{"val": getattr(by_month.get(m, None), f, "") if by_month.get(m) else "",
                                 "sub_id": by_month.get(m).id if by_month.get(m) else None,
                                 "month": m,
                                 "year": year}
                                for m in range(1, 13)]}
                    for f in fields]
            groups.append({"title": title, "rows": rows})
        ctx.update({
            "directorate": d, "selected_year": year, "subcategory": "socioeducativo",
            "month_labels": [l for _, l in MONTH_LABELS], "table_groups": groups,
            "can_delete": self.is_admin(),
        })
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
        
        # Resolve the directorate (Proteção Especial)
        directorate = Directorate.objects.filter(name__icontains="Proteção Especial").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="CREAS").first()
        
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
        
        try:
            report.user_id = request.user.pk
        except Exception:
            pass
        report.created_by = request.user.email or request.user.username
        
        # Save triggers model customsave calculations
        report.save()
        
        # Return all computed fields as well so the client side could know if it wants
        computed_fields = {}
        if self.model == CreasProtetivoReport:
            computed_fields = {
                "fam_atual": report.fam_atual,
                "atend_atual": report.atend_atual
            }
        else:
            computed_fields = {
                "fam_total_acompanhamento": report.fam_total_acompanhamento,
                "masc_total_parcial": report.masc_total_parcial,
                "fem_total_parcial": report.fem_total_parcial,
                "med_masc_la_total_parcial": report.med_masc_la_total_parcial,
                "med_masc_psc_total_parcial": report.med_masc_psc_total_parcial,
                "med_fem_la_total_parcial": report.med_fem_la_total_parcial,
                "med_fem_psc_total_parcial": report.med_fem_psc_total_parcial,
                "med_total_la_geral": report.med_total_la_geral,
                "med_total_psc_geral": report.med_total_psc_geral
            }
            
        return JsonResponse({
            "status": "success", 
            "value": value, 
            "sub_id": report.id,
            "computed": computed_fields
        })


class CreasProtetivoQuickEditView(CreasSharedQuickEditView):
    model = CreasProtetivoReport


class CreasSocioeducativoQuickEditView(CreasSharedQuickEditView):
    model = CreasSocioeducativoReport

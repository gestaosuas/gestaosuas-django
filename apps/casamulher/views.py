import uuid
from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from apps.directorates.models import Directorate

from .models import CasaDaMulherReport, DiversidadeReport, NucleoDiversidadeReport
from .forms import CasaDaMulherForm, DiversidadeForm, NucleoDiversidadeForm

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


class CasaMulherBaseMixin(DirectorateAccessMixin):
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


class CasaMulherHomeView(TvTemplateMixin, CasaMulherBaseMixin, DetailView):
    template_name = "casamulher/home.html"
    tv_template_name = "casamulher/tv.html"
    context_object_name = "directorate"

    def get_object(self, queryset=None):
        return self.get_directorate()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        directorate = self.object
        year = self.get_year()
        month = self.get_month()
        month_num = self.get_month_number()

        cm_qs = CasaDaMulherReport.objects.filter(directorate=directorate, year=year).order_by("month")
        div_qs = DiversidadeReport.objects.filter(directorate=directorate, year=year).order_by("month")
        nd_qs = NucleoDiversidadeReport.objects.filter(directorate=directorate, year=year).order_by("month")

        cm_by_month = {r.month: r for r in cm_qs}
        div_by_month = {r.month: r for r in div_qs}
        nd_by_month = {r.month: r for r in nd_qs}

        years_qs = build_year_range([
            CasaDaMulherReport.objects.filter(directorate=directorate),
            DiversidadeReport.objects.filter(directorate=directorate),
            NucleoDiversidadeReport.objects.filter(directorate=directorate)
        ], year)

        def get_val(qs_by_month, field):
            if month == "all":
                return sum(safe_int(qs_by_month.get(m, None) and getattr(qs_by_month[m], field, 0)) for m in range(1, 13))
            r = qs_by_month.get(int(month))
            return safe_int(getattr(r, field, 0)) if r else 0

        def get_history(qs_by_month, field):
            return [safe_int(getattr(qs_by_month.get(m, None), field, 0) if qs_by_month.get(m) else 0) for m in range(1, 13)]

        # KPI 1: Casa da Mulher (Mulheres Atendidas)
        cm_atend_hist = get_history(cm_by_month, "cm_atend_mulheres_atendidas")
        if month == "all":
            nonzero_cm = [v for v in cm_atend_hist if v > 0]
            cm_atend = nonzero_cm[-1] if nonzero_cm else 0
        else:
            cm_atend = get_val(cm_by_month, "cm_atend_mulheres_atendidas")

        # KPI 2: Atendimentos Diversos (Pessoas Atendidas)
        div_atend_hist = get_history(div_by_month, "div_atend_mulheres_atendidas")
        if month == "all":
            nonzero_div = [v for v in div_atend_hist if v > 0]
            div_atend = nonzero_div[-1] if nonzero_div else 0
        else:
            div_atend = get_val(div_by_month, "div_atend_mulheres_atendidas")

        # KPI 3: Núcleo de Diversidade (Pessoas Atendidas)
        nd_atend_hist = get_history(nd_by_month, "nd_pessoas_atendidas")
        if month == "all":
            nonzero_nd = [v for v in nd_atend_hist if v > 0]
            nd_atend = nonzero_nd[-1] if nonzero_nd else 0
        else:
            nd_atend = get_val(nd_by_month, "nd_pessoas_atendidas")

        cards = [
            {
                "label": f"Casa da Mulher (Atendidas em {month_name(month_num) if month != 'all' else 'Último'})",
                "value": cm_atend, "sparkline": build_sparkline(cm_atend_hist),
                "icon": "woman", "color": "#ec4899",  # Pink
                "variation": build_variation(cm_atend_hist, month)
            },
            {
                "label": f"Atendimentos Diversos (Atendidos em {month_name(month_num) if month != 'all' else 'Último'})",
                "value": div_atend, "sparkline": build_sparkline(div_atend_hist),
                "icon": "people", "color": "#6366f1",  # Indigo
                "variation": build_variation(div_atend_hist, month)
            },
            {
                "label": f"Núcleo de Diversidade (Atendidos em {month_name(month_num) if month != 'all' else 'Último'})",
                "value": nd_atend, "sparkline": build_sparkline(nd_atend_hist),
                "icon": "finger-print", "color": "#a855f7",  # Purple
                "variation": build_variation(nd_atend_hist, month)
            },
        ]

        # Doughnut 1: Tipos de Violência (Casa da Mulher)
        violence_fields = [
            ("Física", "cm_violencia_fisica"),
            ("Moral", "cm_violencia_moral"),
            ("Psicológica", "cm_violencia_psicologica"),
            ("Sexual", "cm_violencia_sexual"),
            ("Patrimonial", "cm_violencia_patrimonial"),
            ("Nenhuma/Outras", ["cm_violencia_nenhuma", "cm_violencia_outras"]),
        ]
        donut_colors = ["#ec4899", "#a855f7", "#6366f1", "#f43f5e", "#e11d48", "#9ca3af"]
        donut_violence_items = []
        for (label, fields), color in zip(violence_fields, donut_colors):
            if isinstance(fields, list):
                total_val = sum(get_val(cm_by_month, f) for f in fields)
            else:
                total_val = get_val(cm_by_month, fields)
            if total_val > 0:
                donut_violence_items.append({"label": label, "value": total_val, "color": color})

        # Doughnut 2: Situação da Demanda (Atendimentos Diversos)
        demand_fields = [
            ("Violência Infrafamiliar", "div_sit_violencia_infrafamiliar"),
            ("Violência Extrafamiliar", "div_sit_violencia_extrafamiliar"),
            ("Fora do Contexto", "div_sit_demanda_fora_contexto"),
        ]
        donut_demand_colors = ["#f43f5e", "#3b82f6", "#10b981"]
        donut_demand_items = []
        for (label, f), color in zip(demand_fields, donut_demand_colors):
            total_val = get_val(div_by_month, f)
            if total_val > 0:
                donut_demand_items.append({"label": label, "value": total_val, "color": color})

        # Bar 1: Faixa Etária (Combined or Casa da Mulher primary)
        age_labels_fields = [
            ("16-17", "cm_faixa_16_17"),
            ("18-30", "cm_faixa_18_30"),
            ("31-40", "cm_faixa_31_40"),
            ("41-50", "cm_faixa_41_50"),
            ("51-60", "cm_faixa_51_60"),
            ("60+", "cm_faixa_acima_60"),
            ("Não Consta", "cm_faixa_nao_consta"),
        ]
        bar_age_items = []
        for label, f in age_labels_fields:
            val = get_val(cm_by_month, f)
            bar_age_items.append({"label": label, "value": val, "color": "#ec4899"})

        # Bar 2: Cor/Raça (Casa da Mulher)
        race_labels_fields = [
            ("Branca", "cm_raca_branca"),
            ("Preta", "cm_raca_preta"),
            ("Parda", "cm_raca_parda"),
            ("Amarela", "cm_raca_amarelo"),
            ("Indígena", "cm_raca_indigena"),
            ("Não Consta", "cm_raca_nao_consta"),
        ]
        bar_race_items = []
        for label, f in race_labels_fields:
            val = get_val(cm_by_month, f)
            bar_race_items.append({"label": label, "value": val, "color": "#6366f1"})

        ctx.update({
            "selected_year": year, "selected_month": month,
            "months_range": MONTH_OPTIONS, "years_range": years_qs,
            "cards": cards,
            "donut_violence_items": donut_violence_items,
            "donut_demand_items": donut_demand_items,
            "bar_age_items": bar_age_items,
            "bar_race_items": bar_race_items,
            "period_label": period_label(year, month),
        })
        return ctx


class CasaMulherGenericFormView(CasaMulherBaseMixin, FormView):
    template_name = "casamulher/form.html"
    subcategory = ""
    success_msg = ""

    def get_initial(self):
        initial = super().get_initial()
        initial["month"] = self.get_month_number()
        initial["year"] = self.get_year()
        r = self.form_class.Meta.model.objects.filter(
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
            "subcategory": self.subcategory, "selected_year": self.get_year(), "selected_month": self.get_month_number()
        })
        return ctx

    def form_valid(self, form):
        d = self.get_directorate()
        r, created = self.form_class.Meta.model.objects.get_or_create(
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
        messages.success(self.request, self.success_msg)
        return redirect(reverse("casamulher:home", kwargs={"pk": d.pk}) + f"?year={form.cleaned_data['year']}")


class CasaDaMulherFormView(CasaMulherGenericFormView):
    form_class = CasaDaMulherForm
    subcategory = "casa-da-mulher"
    success_msg = "Dados Casa da Mulher salvos com sucesso."


class DiversidadeFormView(CasaMulherGenericFormView):
    form_class = DiversidadeForm
    subcategory = "diversidade"
    success_msg = "Dados Atendimentos Diversos salvos com sucesso."


class NucleoDiversidadeFormView(CasaMulherGenericFormView):
    form_class = NucleoDiversidadeForm
    subcategory = "nucleo-diversidade"
    success_msg = "Dados Núcleo de Diversidade salvos com sucesso."


class CasaMulherGenericDataView(CasaMulherBaseMixin, TemplateView):
    template_name = "casamulher/data.html"
    form_class = None
    model = None
    subcategory = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.get_directorate()
        year = self.get_year()
        reports = self.model.objects.filter(directorate=d, year=year).order_by("month")
        by_month = {r.month: r for r in reports}
        groups = []
        for title, fields in self.form_class.section_map:
            rows = [{"label": self.form_class.labels.get(f, f),
                     "key": f,
                     "is_readonly": False,  # All are editable in casamulher tables
                     "values": [{"val": getattr(by_month.get(m, None), f, "") if by_month.get(m) else "",
                                 "sub_id": by_month.get(m).id if by_month.get(m) else None,
                                 "month": m,
                                 "year": year}
                                for m in range(1, 13)]}
                    for f in fields]
            groups.append({"title": title, "rows": rows})
        ctx.update({
            "directorate": d, "selected_year": year, "subcategory": self.subcategory,
            "month_labels": [l for _, l in MONTH_LABELS], "table_groups": groups,
            "can_delete": self.is_admin(),
        })
        return ctx


class CasaDaMulherDataView(CasaMulherGenericDataView):
    form_class = CasaDaMulherForm
    model = CasaDaMulherReport
    subcategory = "casa-da-mulher"


class DiversidadeDataView(CasaMulherGenericDataView):
    form_class = DiversidadeForm
    model = DiversidadeReport
    subcategory = "diversidade"


class NucleoDiversidadeDataView(CasaMulherGenericDataView):
    form_class = NucleoDiversidadeForm
    model = NucleoDiversidadeReport
    subcategory = "nucleo-diversidade"


class CasaMulherSharedQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]
    model = None

    def post(self, request):
        sub_id = request.POST.get("sub_id")
        key = request.POST.get("key")
        value_str = request.POST.get("value")
        value = int(value_str) if value_str and value_str.isdigit() else 0
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        
        # Resolve the directorate (Casa da Mulher)
        directorate_pk = request.POST.get("directorate_id")
        if directorate_pk:
            directorate = get_object_or_404(Directorate, id=directorate_pk)
        else:
            directorate = Directorate.objects.filter(name__icontains="Mulher").first()
            if not directorate:
                directorate = Directorate.objects.filter(name__icontains="CREAS").first()
        
        if sub_id and sub_id != "None" and sub_id != "":
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
        
        report.save()
        
        return JsonResponse({
            "status": "success", 
            "value": value, 
            "sub_id": report.id,
            "computed": {}
        })


class CasaDaMulherQuickEditView(CasaMulherSharedQuickEditView):
    model = CasaDaMulherReport


class DiversidadeQuickEditView(CasaMulherSharedQuickEditView):
    model = DiversidadeReport


class NucleoDiversidadeQuickEditView(CasaMulherSharedQuickEditView):
    model = NucleoDiversidadeReport

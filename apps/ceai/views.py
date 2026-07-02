# Views for the CEAI module - Centro de Apoio ao Idoso
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from apps.directorates.models import Directorate, MonthlyReport
from apps.ceai.models import CeaiCategory, CeaiOficina, Submission
from apps.ceai.constants import CEAI_UNITS, CEAI_FORM_DEFINITION, CONDOMINIO_IDOSO_FORM_DEFINITION
from apps.accounts.mixins import RoleRequiredMixin
from apps.core.mixins import TvTemplateMixin

class CeaiDashboardView(TvTemplateMixin, LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "ceai/dashboard.html"
    tv_template_name = "ceai/tv.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = get_object_or_404(Directorate, name__icontains="CEAI")
        context["directorate"] = directorate
        context["units"] = CEAI_UNITS
        
        # Filters
        now = timezone.now()
        selected_year = int(self.request.GET.get("year", now.year))
        selected_month = self.request.GET.get("month", "all")
        selected_unit = self.request.GET.get("unit", "all")
        
        context["selected_year"] = selected_year
        context["selected_month"] = selected_month
        context["selected_unit"] = selected_unit
        context["current_year"] = now.year
        context["months_range"] = [
            (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
            (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
            (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
        ]
        context["years_range"] = range(2023, now.year + 1)

        # Fetch submissions for the year
        submissions = Submission.objects.filter(
            directorate_id=directorate.id,
            year=selected_year
        ).order_by("month")

        # Process monthly data for charts
        month_names = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        chart_series = {
            "admissões": [0] * 12,
            "desligamentos": [0] * 12,
            "atendimentos": [0] * 12,
            "total_idosos": [0] * 12
        }

        summary = {
            "admitidos_masc": 0, "admitidos_fem": 0,
            "total_idosos": 0, "atendidos_mes": 0, "desligados": 0
        }

        def safe_int(value):
            try:
                if isinstance(value, str):
                    # Remove thousand separators if any (dots) and replace comma with dot for float conversion
                    # But wait, in Brazil dot is thousands and comma is decimal.
                    # Or it could be just a float string from JS '3.0'.
                    # Let's try to convert to float first.
                    clean_val = value.replace('.', '').replace(',', '.') if '.' in value and ',' in value else value.replace(',', '.')
                    return int(float(clean_val))
                return int(value or 0)
            except (ValueError, TypeError):
                # If conversion fails, try one more time just float
                try:
                    return int(float(value))
                except:
                    return 0

        # Track which month was the last processed to get correct snapshot for summary
        last_month_processed = 0

        # Data for Pie Chart (Atendimentos por Unidade)
        atendimentos_por_unidade = {}

        for sub in submissions:
            m_idx = sub.month - 1
            data = sub.data
            
            # Identify units in this submission
            units_in_sub = []
            if data.get("_is_multi_unit") and "units" in data:
                for u_name, u_data in data["units"].items():
                    units_in_sub.append((u_name, u_data))
            else:
                u_name = data.get("_unit", "Geral")
                units_in_sub.append((u_name, data))

            month_total_idosos = 0
            for u_name, u_data in units_in_sub:
                # Apply unit filter if not "all"
                if selected_unit != "all" and u_name != selected_unit:
                    continue

                # Accumulate for chart
                adm = safe_int(u_data.get("inseridos_masc", 0)) + safe_int(u_data.get("inseridos_fem", 0))
                desl = safe_int(u_data.get("desligados_masc", 0)) + safe_int(u_data.get("desligados_fem", 0))
                aten = safe_int(u_data.get("total_atendimentos", 0))
                total = safe_int(u_data.get("total_inseridos", 0))

                chart_series["admissões"][m_idx] += adm
                chart_series["desligamentos"][m_idx] += desl
                chart_series["atendimentos"][m_idx] += aten
                chart_series["total_idosos"][m_idx] += total
                month_total_idosos += total

                # Track for pie chart (only if within selected month range)
                if selected_month == "all" or int(selected_month) == sub.month:
                    atendimentos_por_unidade[u_name] = atendimentos_por_unidade.get(u_name, 0) + aten

                # Update summary
                if selected_month != "all" and int(selected_month) == sub.month:
                    summary["admitidos_masc"] += safe_int(u_data.get("inseridos_masc", 0))
                    summary["admitidos_fem"] += safe_int(u_data.get("inseridos_fem", 0))
                    summary["atendidos_mes"] += aten
                    summary["desligados"] += desl
                    summary["total_idosos"] += total
                elif selected_month == "all":
                    summary["admitidos_masc"] += safe_int(u_data.get("inseridos_masc", 0))
                    summary["admitidos_fem"] += safe_int(u_data.get("inseridos_fem", 0))
                    summary["atendidos_mes"] += aten
                    summary["desligados"] += desl
                    
            if selected_month == "all" and sub.month >= last_month_processed:
                summary["total_idosos"] = month_total_idosos
                last_month_processed = sub.month

        # Format for Chart.js
        context["line_chart_admissoes"] = [{"label": month_names[i], "value": v} for i, v in enumerate(chart_series["admissões"])]
        context["line_chart_desligamentos"] = [{"label": month_names[i], "value": v} for i, v in enumerate(chart_series["desligamentos"])]
        context["line_chart_atendimentos"] = [{"label": month_names[i], "value": v} for i, v in enumerate(chart_series["atendimentos"])]
        context["line_chart_total_idosos"] = [{"label": month_names[i], "value": v} for i, v in enumerate(chart_series["total_idosos"])]
        context["pie_chart_atendimentos"] = [{"label": k, "value": v} for k, v in atendimentos_por_unidade.items()]
        
        context["summary"] = summary
        return context

class CeaiUpdateDataView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "diretor", "agente"]

    def get(self, request, unit):
        directorate = get_object_or_404(Directorate, name__icontains="CEAI")
        now = timezone.now()
        month = int(request.GET.get("month", now.month))
        year = int(request.GET.get("year", now.year))
        
        submission = Submission.objects.filter(
            directorate_id=directorate.id,
            month=month,
            year=year
        ).first()
        
        initial_data = {}
        if submission and "units" in submission.data and unit in submission.data["units"]:
            initial_data = submission.data["units"][unit]
            
        form_def = CEAI_FORM_DEFINITION
        if unit == "Condomínio do Idoso":
            form_def = CONDOMINIO_IDOSO_FORM_DEFINITION
            context_oficinas = []
        else:
            # For territorial units, fetch registered offices
            oficinas = CeaiOficina.objects.filter(unit=unit).order_by("activity_name")
            context_oficinas = []
            for ofi in oficinas:
                context_oficinas.append({
                    "id": f"ofi_{ofi.id}",
                    "label": ofi.activity_name,
                    "category": ofi.category.name if ofi.category else "Sem Categoria",
                    "initial_vagas": initial_data.get(f"ofi_{ofi.id}_vagas", ofi.total_vacancies),
                    "initial_ocupacao": initial_data.get(f"ofi_{ofi.id}_ocupacao", ofi.vacancies)
                })
            
        return render(request, "ceai/update_data.html", {
            "unit": unit,
            "directorate": directorate,
            "form_def": form_def,
            "oficinas": context_oficinas,
            "initial_data": initial_data,
            "month": month,
            "year": year
        })

    def post(self, request, unit):
        directorate = get_object_or_404(Directorate, name__icontains="CEAI")
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        
        # Collect form data
        form_data = {}
        for key, value in request.POST.items():
            if not key in ["csrfmiddlewaretoken", "month", "year"]:
                form_data[key] = value
        
        # Set metadata for the submission
        form_data["_unit"] = unit
        form_data["_setor"] = "ceai"
        
        # Get or create submission
        submission, created = Submission.objects.get_or_create(
            directorate_id=directorate.id,
            month=month,
            year=year,
            defaults={
                "user": request.user,
                "data": {
                    "_is_multi_unit": True,
                    "units": {
                        unit: form_data
                    },
                    "_setor": "ceai",
                    "_has_ceai": True
                }
            }
        )
        
        if not created:
            # Update existing JSONB
            data = submission.data
            if "units" not in data:
                data["units"] = {}
            data["units"][unit] = form_data
            data["_is_multi_unit"] = True
            data["_has_ceai"] = True
            submission.data = data
            submission.save()
            
        return redirect("ceai:dashboard")

class CeaiCategoryApiView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "diretor", "agente"]

    def get(self, request):
        unit = request.GET.get("unit")
        categories = CeaiCategory.objects.filter(unit=unit).order_by("name")
        data = [{"id": str(c.id), "name": c.name} for c in categories]
        return JsonResponse(data, safe=False)

    def post(self, request):
        data = json.loads(request.body)
        unit = data.get("unit")
        name = data.get("name")
        cat_id = data.get("id")

        if cat_id:
            # Update
            category = get_object_or_404(CeaiCategory, id=cat_id)
            category.name = name
            category.save()
        else:
            # Create
            CeaiCategory.objects.create(unit=unit, name=name)
        
        return JsonResponse({"success": True})

    def delete(self, request):
        cat_id = request.GET.get("id")
        category = get_object_or_404(CeaiCategory, id=cat_id)
        # Check for linked offices before deleting
        if CeaiOficina.objects.filter(category=category).exists():
            return JsonResponse({"success": False, "error": "Existem oficinas vinculadas a esta categoria."}, status=400)
        category.delete()
        return JsonResponse({"success": True})

class CeaiOficinaApiView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "diretor", "agente"]

    def get(self, request):
        unit = request.GET.get("unit")
        oficinas = CeaiOficina.objects.filter(unit=unit).select_related("category").order_by("activity_name")
        data = [{
            "id": str(o.id),
            "activity_name": o.activity_name,
            "category_id": str(o.category.id) if o.category else None,
            "category_name": o.category.name if o.category else None
        } for o in oficinas]
        return JsonResponse(data, safe=False)

    def post(self, request):
        data = json.loads(request.body)
        unit = data.get("unit")
        activity_name = data.get("activity_name")
        category_id = data.get("category_id")
        ofi_id = data.get("id")

        category = None
        if category_id and category_id != "empty":
            category = get_object_or_404(CeaiCategory, id=category_id)

        if ofi_id:
            # Update
            oficina = get_object_or_404(CeaiOficina, id=ofi_id)
            oficina.activity_name = activity_name
            oficina.category = category
            oficina.save()
        else:
            # Create
            CeaiOficina.objects.create(
                unit=unit,
                activity_name=activity_name,
                category=category,
                total_vacancies=0,
                vacancies=0
            )
        
        return JsonResponse({"success": True})

    def delete(self, request):
        ofi_id = request.GET.get("id")
        oficina = get_object_or_404(CeaiOficina, id=ofi_id)
        oficina.delete()
        return JsonResponse({"success": True})

class CeaiOficinasView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "ceai/oficinas.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.kwargs.get("unit")
        context["unit"] = unit
        context["categories"] = CeaiCategory.objects.filter(unit=unit).order_by("name")
        context["oficinas"] = CeaiOficina.objects.filter(unit=unit).select_related("category").order_by("activity_name")
        return context

class CeaiCategoriesView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "ceai/categories.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.kwargs.get("unit")
        context["unit"] = unit
        context["categories"] = CeaiCategory.objects.filter(unit=unit).order_by("name")
        return context

class CeaiMonthlyNarrativeView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = "ceai/monthly_report.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get(self, request, pk):
        directorate = get_object_or_404(Directorate, pk=pk)
        month = int(request.GET.get("month", timezone.now().month))
        year = int(request.GET.get("year", timezone.now().year))
        
        report = MonthlyReport.objects.filter(
            directorate=directorate, 
            setor="ceai", 
            year=year, 
            month=month
        ).first()
        
        history = MonthlyReport.objects.filter(
            directorate=directorate, 
            setor="ceai"
        ).order_by("-year", "-month")[:8]
        
        return render(request, self.template_name, {
            "directorate": directorate,
            "report": report,
            "month": month,
            "year": year,
            "history": history,
            "months_range": [
                (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
                (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
                (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
            ],
            "years_range": range(2023, timezone.now().year + 1)
        })

    def post(self, request, pk):
        directorate = get_object_or_404(Directorate, pk=pk)
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        content = request.POST.get("content")
        
        MonthlyReport.objects.update_or_create(
            directorate=directorate,
            setor="ceai",
            year=year,
            month=month,
            defaults={
                "content": content,
                "user_id": request.user.id,
                "status": "finalized"
            }
        )
        
        return redirect("ceai:dashboard")

class CeaiDataListView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "ceai/data_list.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit_filter = self.request.GET.get("unit", "all")
        category_filter = self.request.GET.get("category", "all")
        year = int(self.request.GET.get("year", timezone.now().year))
        directorate = Directorate.objects.filter(name__icontains="CEAI").first()
        
        submissions = Submission.objects.filter(
            directorate_id=directorate.id,
            year=year
        ).order_by("month")

        all_territorial_units = ["Brasil", "Laranjeiras", "Luizote", "Guarani", "Morumbi"]
        units_to_process = all_territorial_units if unit_filter == "all" else [unit_filter]

        indicators_def = [
            {"label": "MATRICULADOS NO 1º DIA DO MÊS (MASC)", "key": "atendidos_anterior_masc", "type": "stock"},
            {"label": "MATRICULADOS NO 1º DIA DO MÊS (FEM)", "key": "atendidos_anterior_fem", "type": "stock"},
            {"label": "INSERIDOS NO MÊS (MASC)", "key": "inseridos_masc", "type": "flow"},
            {"label": "INSERIDOS NO MÊS (FEM)", "key": "inseridos_fem", "type": "flow"},
            {"label": "DESLIGADOS (MASC)", "key": "desligados_masc", "type": "flow"},
            {"label": "DESLIGADOS (FEM)", "key": "desligados_fem", "type": "flow"},
            {"label": "TOTAL DE IDOSOS ATENDIDOS (ANO)", "key": "total_inseridos", "type": "stock"},
            {"label": "ATENDIMENTOS", "key": "total_atendimentos", "type": "flow"},
        ]

        units_data = []
        for u_name in units_to_process:
            unit_payload = {"name": u_name, "matrix": [], "oficinas": {"available": [], "occupied": []}}
            
            # Indicators Matrix for this unit
            for ind in indicators_def:
                row = {"label": ind["label"], "key": ind["key"], "months": [{"val": 0, "sub_id": None, "month": i+1, "year": year} for i in range(12)], "total": 0}
                for sub in submissions:
                    m_idx = sub.month - 1
                    val = 0
                    if sub.data.get("_is_multi_unit") and "units" in sub.data:
                        val = safe_int(sub.data["units"].get(u_name, {}).get(ind["key"], 0))
                    elif sub.data.get("_unit") == u_name:
                        val = safe_int(sub.data.get(ind["key"], 0))
                    
                    row["months"][m_idx]["val"] = val
                    row["months"][m_idx]["sub_id"] = sub.id
                
                # Calculate total for matrix
                vals = [m["val"] for m in row["months"]]
                if ind["type"] == "flow":
                    row["total"] = sum(vals)
                else:
                    for v in reversed(vals):
                        if v > 0: row["total"] = v; break
                unit_payload["matrix"].append(row)

            # Workshops Matrix for this unit
            oficinas = CeaiOficina.objects.filter(unit=u_name).select_related("category").order_by("activity_name")
            if category_filter != "all":
                oficinas = oficinas.filter(category__name=category_filter)

            for ofi in oficinas:
                avail_row = {"label": ofi.activity_name, "category": ofi.category.name if ofi.category else "-", "key": f"ofi_{ofi.id}_vagas", "months": [{"val": 0, "sub_id": None, "month": i+1, "year": year} for i in range(12)]}
                occu_row = {"label": ofi.activity_name, "category": ofi.category.name if ofi.category else "-", "key": f"ofi_{ofi.id}_ocupacao", "months": [{"val": 0, "sub_id": None, "month": i+1, "year": year} for i in range(12)]}
                
                for sub in submissions:
                    m_idx = sub.month - 1
                    u_data = {}
                    if sub.data.get("_is_multi_unit") and "units" in sub.data:
                        u_data = sub.data["units"].get(u_name, {})
                    elif sub.data.get("_unit") == u_name:
                        u_data = sub.data
                    
                    avail_row["months"][m_idx]["val"] = safe_int(u_data.get(avail_row["key"], ofi.total_vacancies))
                    avail_row["months"][m_idx]["sub_id"] = sub.id
                    occu_row["months"][m_idx]["val"] = safe_int(u_data.get(occu_row["key"], ofi.vacancies))
                    occu_row["months"][m_idx]["sub_id"] = sub.id
                
                unit_payload["oficinas"]["available"].append(avail_row)
                unit_payload["oficinas"]["occupied"].append(occu_row)
            
            units_data.append(unit_payload)

        context["units_data"] = units_data
        context["unit_filter"] = unit_filter
        context["category_filter"] = category_filter
        context["selected_year"] = year
        context["directorate"] = directorate
        context["month_headers"] = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        context["years_range"] = range(2023, timezone.now().year + 1)
        context["all_categories"] = CeaiCategory.objects.values_list("name", flat=True).distinct().order_by("name")
        return context

class CeaiQuickEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin"]

    def post(self, request):
        sub_id = request.POST.get("sub_id")
        unit = request.POST.get("unit")
        key = request.POST.get("key")
        value = safe_int(request.POST.get("value"))
        month = request.POST.get("month")
        year = request.POST.get("year")
        
        # Tenta encontrar a diretoria pelo nome de forma robusta
        directorate = Directorate.objects.filter(name__icontains="CEAI").first()
        if not directorate:
            directorate = Directorate.objects.filter(name__icontains="Proteção Social Especial").first()
        
        if sub_id and sub_id != "None":
            submission = get_object_or_404(Submission, id=sub_id)
        else:
            # Check if exists for this month/year anyway
            submission = Submission.objects.filter(
                directorate_id=directorate.id,
                month=month,
                year=year
            ).first()
            
            if not submission:
                # Create new submission
                # Note: Defaulting to multi-unit if multiple units exist in CEAI
                submission = Submission(
                    directorate_id=directorate.id,
                    month=month,
                    year=year,
                    data={"_is_multi_unit": True, "units": {}}
                )

        data = submission.data

        if data.get("_is_multi_unit") and "units" in data:
            if unit not in data["units"]:
                data["units"][unit] = {}
            data["units"][unit][key] = value
        else:
            data[key] = value
        
        submission.data = data
        submission.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": submission.id})

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return int(float(value))
        except:
            return 0
class CeaiReportsListView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "ceai/reports.html"
    allowed_roles = ["admin", "diretor", "agente"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = Directorate.objects.filter(name__icontains="CEAI").first()
        context["directorate"] = directorate
        context["reports"] = MonthlyReport.objects.filter(
            directorate=directorate, 
            setor="ceai"
        ).order_by("-year", "-month")
        return context

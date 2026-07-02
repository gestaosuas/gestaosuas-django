from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.contrib import messages
from apps.accounts.mixins import RoleRequiredMixin, DirectorateAccessMixin
from apps.core.mixins import TvTemplateMixin
from apps.directorates.models import Directorate
from .models import PopRuaReport
from .forms import PopRuaForm
import json


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
        
        reports_query = PopRuaReport.objects.filter(directorate=directorate, year=year)
        
        # Monthly charts data (always show full year evolution)
        months_labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        atend_centro = [0]*12
        atend_abordagem = [0]*12
        atend_migracao = [0]*12
        persistentes_mensal = [0]*12
        
        all_reports = reports_query.order_by("month")
        for r in all_reports:
            m_idx = r.month - 1
            atend_centro[m_idx] = r.num_atend_centro_ref or 0
            atend_abordagem[m_idx] = r.num_atend_abordagem or 0
            atend_migracao[m_idx] = r.num_atend_migracao or 0
            persistentes_mensal[m_idx] = r.ar_persistentes or 0

        context["chart_labels"] = json.dumps(months_labels)
        context["chart_centro"] = json.dumps(atend_centro)
        context["chart_abordagem"] = json.dumps(atend_abordagem)
        context["chart_migracao"] = json.dumps(atend_migracao)
        context["persistentes_data"] = json.dumps(persistentes_mensal)

        # Filtered totals for cards and doughnut
        if month_param != "all":
            target_month = int(month_param)
            filtered_reports = reports_query.filter(month=target_month)
        else:
            filtered_reports = reports_query

        total_cr = 0
        total_as = 0
        total_nm = 0
        drogas_cr = 0
        drogas_ar = 0
        
        for r in filtered_reports:
            total_cr += r.num_atend_centro_ref or 0
            total_as += r.num_atend_abordagem or 0
            total_nm += r.num_atend_migracao or 0
            drogas_cr += r.cr_b1_drogas or 0
            drogas_ar += r.ar_e5_drogas or 0

        context["total_atend_centro"] = total_cr
        context["total_atend_abordagem"] = total_as
        context["total_atend_migracao"] = total_nm
        context["total_geral"] = total_cr + total_as + total_nm
        
        context["drogas_data"] = json.dumps([drogas_cr, drogas_ar])
        context["drogas_labels"] = json.dumps(["Centro de Referência", "Abordagem Social"])
        
        context["years_range"] = range(2023, timezone.now().year + 1)
        context["months_range"] = [
            (1, "JAN."), (2, "FEV."), (3, "MAR."), (4, "ABR."),
            (5, "MAI."), (6, "JUN."), (7, "JUL."), (8, "AGO."),
            (9, "SET."), (10, "OUT."), (11, "NOV."), (12, "DEZ.")
        ]
        return context

class PopRuaDataListView(PopRuaBaseMixin, TemplateView):
    template_name = "poprua/data_list.html"

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

class PopRuaUpdateView(PopRuaBaseMixin, View):
    def get(self, request, pk=None):
        directorate = self.get_directorate()
        report = None
        if pk:
            report = get_object_or_404(PopRuaReport, pk=pk)
        
        initial = {}
        if not report:
            initial["year"] = timezone.now().year
            
        form = PopRuaForm(instance=report, initial=initial)
        return render(request, "poprua/form.html", {
            "form": form,
            "directorate": directorate,
            "report": report
        })

    def post(self, request, pk=None):
        directorate = self.get_directorate()
        report = None
        
        # Primary check: ID based
        if pk:
            report = get_object_or_404(PopRuaReport, pk=pk)
            
        form = PopRuaForm(request.POST, instance=report)
        if form.is_valid():
            # Secondary check: Monthly/Yearly uniqueness (Upsert logic)
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]
            
            existing = PopRuaReport.objects.filter(directorate=directorate, month=month, year=year).first()
            if existing and (not report or existing.id != report.id):
                # We found an existing record that is not the one we are editing
                # Switch instance to the existing one to update it instead of creating duplicate
                form = PopRuaForm(request.POST, instance=existing)
                # Re-validate just in case, though it should be valid
                form.is_valid()

            new_report = form.save(commit=False)
            new_report.directorate = directorate
            new_report.created_by = request.user
            new_report.save()
            messages.success(request, "Dados salvos com sucesso no banco de dados!")
            return redirect("poprua:dashboard")
        else:
            error_msg = "Erro ao salvar dados. Verifique os campos: "
            error_fields = [form.fields[f].label for f in form.errors]
            messages.error(request, error_msg + ", ".join(error_fields))
        
        return render(request, "poprua/form.html", {
            "form": form,
            "directorate": directorate,
            "report": report
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
        
        if sub_id and sub_id != "None" and sub_id != "":
            report = get_object_or_404(PopRuaReport, id=sub_id)
        else:
            report, _ = PopRuaReport.objects.get_or_create(
                directorate=directorate,
                month=month,
                year=year
            )

        setattr(report, key, value)
        report.save()
        return JsonResponse({"status": "success", "value": value, "sub_id": report.id})

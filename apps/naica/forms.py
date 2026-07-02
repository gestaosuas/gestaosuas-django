from django import forms
from apps.core.forms import StyledMonitoringForm
from .models import NaicaReport


class NaicaReportForm(StyledMonitoringForm):
    class Meta:
        model = NaicaReport
        exclude = ("id", "directorate", "user_id", "unit_name", "created_by", "created_at", "updated_at", "status")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input", "min": 2020}),
        }

    section_map = [
        (
            "DADOS DO NAICA",
            [
                "mes_anterior_masc",
                "mes_anterior_fem",
                "inseridos_masc",
                "inseridos_fem",
                "desligados_masc",
                "desligados_fem",
                "total_atendidas",
            ],
        ),
        (
            "INDICADORES ADICIONAIS",
            ["atendimentos"],
        ),
    ]

    labels = {
        "mes_anterior_masc": "Masculino em acompanhamento no 1o dia do Mes",
        "mes_anterior_fem": "Feminino em acompanhamento no 1o dia do Mes",
        "inseridos_masc": "Admitidos Masculino",
        "inseridos_fem": "Admitidos Feminino",
        "desligados_masc": "Desligados Masculino",
        "desligados_fem": "Desligados Feminino",
        "total_atendidas": "Total Criancas Inseridas",
        "atendimentos": "Atendimentos",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "total_atendidas" in self.fields:
            self.fields["total_atendidas"].disabled = True
            self.fields["total_atendidas"].widget.attrs["readonly"] = True

    def clean(self):
        cleaned = super().clean()
        masc_ant = int(cleaned.get("mes_anterior_masc") or 0)
        masc_ins = int(cleaned.get("inseridos_masc") or 0)
        masc_des = int(cleaned.get("desligados_masc") or 0)
        fem_ant = int(cleaned.get("mes_anterior_fem") or 0)
        fem_ins = int(cleaned.get("inseridos_fem") or 0)
        fem_des = int(cleaned.get("desligados_fem") or 0)
        masc_ativo = max(0, masc_ant + masc_ins - masc_des)
        fem_ativo = max(0, fem_ant + fem_ins - fem_des)
        cleaned["total_atendidas"] = masc_ativo + fem_ativo
        return cleaned

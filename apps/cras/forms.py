from django import forms
from apps.core.forms import StyledMonitoringForm
from .models import CrasReport


class CrasReportForm(StyledMonitoringForm):
    rma_file = forms.FileField(label="Anexar RMA (PDF)", required=False,
                               widget=forms.FileInput(attrs={"accept": ".pdf"}))

    class Meta:
        model = CrasReport
        exclude = ("id", "directorate", "user_external_id", "rma_url", "anexo_rma", "created_at", "updated_at")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input", "min": 2020}),
        }

    section_map = [
        (
            "DADOS DO CRAS",
            [
                "mes_anterior", "admitidas", "desligadas", "atual",
                "atendimentos", "visita_domiciliar", "atend_particularizado",
            ],
        ),
        (
            "SERVICOS E BENEFICIOS",
            ["pro_pao", "dmae", "auxilio_documento", "cesta_basica", "fralda", "absorvente"],
        ),
        (
            "ORIENTACOES E CADASTROS",
            ["bpc", "carteirinha_idoso", "passe_livre_deficiente", "cadastros_novos", "recadastros"],
        ),
    ]

    labels = {
        "mes_anterior": "Mes Anterior (Sugestao: Atual - Desligadas)",
        "admitidas": "Familias Inseridas (PAIF)",
        "desligadas": "Familias Desligadas (PAIF)",
        "atual": "Atual (Mes Anterior + Admitidas)",
        "atendimentos": "Atendimentos",
        "visita_domiciliar": "Visita Domiciliar",
        "atend_particularizado": "Atend. Particularizado",
        "pro_pao": "Pro Pao (Cestas Entregues)",
        "dmae": "DMAE",
        "auxilio_documento": "Auxilio Documento",
        "cesta_basica": "Cesta Basica",
        "fralda": "Fralda",
        "absorvente": "Absorvente",
        "bpc": "BPC (Orientacoes)",
        "carteirinha_idoso": "Carteirinha Idoso",
        "passe_livre_deficiente": "Passe Livre do Deficiente (Orientacoes)",
        "cadastros_novos": "Cadastros Novos",
        "recadastros": "Atualizacao Cadastral",
    }

    help_texts = {
        "mes_anterior": "Preenchido automaticamente: (Atual do mes anterior - Desligadas do mes anterior)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["atual"].disabled = True
        self.fields["atual"].widget.attrs["readonly"] = True
        if "rma_file" in self.fields:
            self.fields["rma_file"].widget = forms.FileInput(attrs={"accept": ".pdf", "class": "form-input"})
            self.fields["rma_file"].initial = None

    def clean(self):
        cleaned = super().clean()
        mes_ant = int(cleaned.get("mes_anterior") or 0)
        admit = int(cleaned.get("admitidas") or 0)
        cleaned["atual"] = mes_ant + admit
        return cleaned

from django import forms
from .models import CreasProtetivoReport, CreasSocioeducativoReport

MONTH_CHOICES = [(1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
                  (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ")]


class CreasProtetivoForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mês", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasProtetivoReport
        exclude = ("id", "directorate", "user_id", "created_by", "status", "created_at", "updated_at")

    section_map = [
        (
            "Famílias em Acompanhamento",
            ["fam_mes_anterior", "fam_admitidas", "fam_desligadas", "fam_atual"]
        ),
        (
            "Direitos Violados (Criança/Adolescente)",
            ["viol_fis_psic_masc", "viol_fis_psic_fem", "abuso_sexual_masc", "abuso_sexual_fem",
             "expl_sexual_masc", "expl_sexual_fem", "negli_aband_masc", "negli_aband_fem",
             "trab_infantil_masc", "trab_infantil_fem"]
        ),
        (
            "Atendimento Criança/Adolescentes",
            ["atend_mes_anterior", "atend_admitidas", "atend_desligadas", "atend_atual"]
        )
    ]

    labels = {
        "fam_mes_anterior": "Mês Anterior",
        "fam_admitidas": "Admitidas",
        "fam_desligadas": "Desligadas",
        "fam_atual": "Atual (Calculado)",
        
        "viol_fis_psic_masc": "Violência Física/Psicológica - Masculino",
        "viol_fis_psic_fem": "Violência Física/Psicológica - Feminino",
        "abuso_sexual_masc": "Abuso Sexual - Masculino",
        "abuso_sexual_fem": "Abuso Sexual - Feminino",
        "expl_sexual_masc": "Exploração Sexual - Masculino",
        "expl_sexual_fem": "Exploração Sexual - Feminino",
        "negli_aband_masc": "Negligência/Abandono - Masculino",
        "negli_aband_fem": "Negligência/Abandono - Feminino",
        "trab_infantil_masc": "Trabalho Infantil - Masculino",
        "trab_infantil_fem": "Trabalho Infantil - Feminino",
        
        "atend_mes_anterior": "Mês Anterior",
        "atend_admitidas": "Admitidas",
        "atend_desligadas": "Desligadas",
        "atend_atual": "Atual (Calculado)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name in {"fam_atual", "atend_atual"}:
                field.disabled = True
                field.widget.attrs["readonly"] = True


class CreasSocioeducativoForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mês", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasSocioeducativoReport
        exclude = ("id", "directorate", "user_id", "created_by", "status", "created_at", "updated_at")

    section_map = [
        (
            "Famílias em Acompanhamento",
            ["fam_acompanhamento_1_dia", "fam_inseridas", "fam_desligadas", "fam_total_acompanhamento"]
        ),
        (
            "Acompanhamento Masculino",
            ["masc_acompanhamento_1_dia", "masc_admitidos", "masc_desligados", "masc_total_parcial"]
        ),
        (
            "Acompanhamento Feminino",
            ["fem_acompanhamento_1_dia", "fem_admitidos", "fem_desligadas", "fem_total_parcial"]
        ),
        (
            "Medidas Masculino",
            ["med_masc_la_andamento", "med_masc_psc_andamento", "med_masc_la_novas", "med_masc_psc_novas",
             "med_masc_la_encerradas", "med_masc_psc_encerradas", "med_masc_la_total_parcial", "med_masc_psc_total_parcial"]
        ),
        (
            "Medidas Feminino",
            ["med_fem_la_andamento", "med_fem_psc_andamento", "med_fem_la_novas", "med_fem_psc_novas",
             "med_fem_la_encerradas", "med_fem_psc_encerradas", "med_fem_la_total_parcial", "med_fem_psc_total_parcial"]
        ),
        (
            "Totais Gerais Medidas",
            ["med_total_la_geral", "med_total_psc_geral"]
        )
    ]

    labels = {
        "fam_acompanhamento_1_dia": "Famílias em acompanhamento no 1º dia do mês",
        "fam_inseridas": "Famílias INSERIDAS no mês",
        "fam_desligadas": "Famílias DESLIGADAS no mês",
        "fam_total_acompanhamento": "TOTAL DE FAMÍLIAS EM ACOMPANHAMENTO",
        
        "masc_acompanhamento_1_dia": "Adolescentes em acompanhamento no 1º dia do mês",
        "masc_admitidos": "Adolescentes admitidos no mês",
        "masc_desligados": "Adolescentes desligados no mês",
        "masc_total_parcial": "Total Parcial",
        
        "fem_acompanhamento_1_dia": "Adolescentes em acompanhamento no 1º dia do mês",
        "fem_admitidos": "Adolescentes admitidos no mês",
        "fem_desligadas": "Adolescentes desligados no mês",
        "fem_total_parcial": "Total Parcial",
        
        "med_masc_la_andamento": "Medidas LA em andamento no 1º dia do mês",
        "med_masc_psc_andamento": "Medidas PSC em andamento no 1º dia do mês",
        "med_masc_la_novas": "Novas medidas LA aplicadas no mês",
        "med_masc_psc_novas": "Novas medidas PSC aplicadas no mês",
        "med_masc_la_encerradas": "Medidas LA encerradas no mês",
        "med_masc_psc_encerradas": "Medidas PSC encerradas no mês",
        "med_masc_la_total_parcial": "Total parcial LA",
        "med_masc_psc_total_parcial": "Total parcial PSC",
        
        "med_fem_la_andamento": "Medidas LA em andamento no 1º dia do mês",
        "med_fem_psc_andamento": "Medidas PSC em andamento no 1º dia do mês",
        "med_fem_la_novas": "Novas medidas LA aplicadas no mês",
        "med_fem_psc_novas": "Novas medidas PSC aplicadas no mês",
        "med_fem_la_encerradas": "Medidas LA encerradas no mês",
        "med_fem_psc_encerradas": "Medidas PSC encerradas no mês",
        "med_fem_la_total_parcial": "Total parcial LA",
        "med_fem_psc_total_parcial": "Total parcial PSC",
        
        "med_total_la_geral": "Total LA (Masc + Fem)",
        "med_total_psc_geral": "Total PSC (Masc + Fem)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            
            # Disable calculated fields
            if name.endswith("_total_parcial") or name.endswith("_geral") or name == "fam_total_acompanhamento":
                field.disabled = True
                field.widget.attrs["readonly"] = True

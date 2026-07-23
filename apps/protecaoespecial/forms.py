from django import forms
from .models import CreasProtetivoReport, CreasSocioeducativoReport

MONTH_CHOICES = [(1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
                  (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ")]

PROTETIVO_VIOLATION_PREFIXES = [
    ("vf", "Crianças/adolescentes vítimas de violência física ou psicológica"),
    ("as", "Crianças/adolescentes vítimas de abuso sexual"),
    ("es", "Crianças/adolescentes vítimas de exploração sexual"),
    ("ng", "Crianças/adolescentes vítimas de negligência ou abandono"),
    ("ti", "Crianças/adolescentes em situação de trabalho infantil"),
]

PROTETIVO_SUBCATEGORIES = [
    ("at", "Atendidas no mês anterior"),
    ("in", "Inseridos / Novos"),
    ("de", "Desligados no PAEFI"),
]

PROTETIVO_GENDERS = [("masc", "Masculino"), ("fem", "Feminino")]
PROTETIVO_AGES = [("0", "0 a 6"), ("7", "7 a 12"), ("13", "13 a 17")]


class CreasProtetivoForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mês", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasProtetivoReport
        exclude = ("id", "directorate", "user_id", "created_by", "status", "created_at", "updated_at")

    labels = {}
    matrix_sections = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name == "fam_atual":
                field.disabled = True
                field.widget.attrs["readonly"] = True

        # Build labels
        self.labels = {
            "fam_mes_anterior": "Famílias em Acomp. 1º Dia Mês",
            "fam_admitidas": "Famílias inseridas (PAEFI)",
            "fam_desligadas": "Famílias desligadas (PAEFI)",
            "fam_atual": "Total de famílias em acompanhamento (PAEFI)",
        }
        for pref, _ in PROTETIVO_VIOLATION_PREFIXES:
            for suf, _ in PROTETIVO_SUBCATEGORIES:
                for g, g_label in PROTETIVO_GENDERS:
                    for a, a_label in PROTETIVO_AGES:
                        self.labels[f"{pref}_{suf}_{g[0]}{a}"] = f"{g_label} {a_label}"

        # Apply labels to fields
        for name, lbl in self.labels.items():
            if name in self.fields:
                self.fields[name].label = lbl

        # Build matrix sections for the view
        self.matrix_sections = []
        for pref, label in PROTETIVO_VIOLATION_PREFIXES:
            self.matrix_sections.append({
                "title": label,
                "prefix": pref,
                "subcategories": PROTETIVO_SUBCATEGORIES,
                "genders": PROTETIVO_GENDERS,
                "ages": PROTETIVO_AGES,
            })

    def clean(self):
        cleaned = super().clean()
        cleaned["fam_atual"] = int(cleaned.get("fam_mes_anterior") or 0) + int(cleaned.get("fam_admitidas") or 0)
        return cleaned


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
            
            if name.endswith("_total_parcial") or name.endswith("_geral") or name == "fam_total_acompanhamento":
                field.disabled = True
                field.widget.attrs["readonly"] = True

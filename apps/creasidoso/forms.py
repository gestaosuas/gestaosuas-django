from django import forms
from .models import CreasIdosoReport, CreasPcdReport

MONTH_CHOICES = [(1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
                  (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ")]

VICTIM_PREFIXES = [
    ("violencia_fisica", "Violencia Fisica ou Psicologica"),
    ("abuso_sexual", "Abuso Sexual"),
    ("exploracao_sexual", "Exploracao Sexual"),
    ("negligencia", "Negligencia ou Abandono"),
    ("exploracao_financeira", "Exploracao Financeira"),
]


class CreasIdosoForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasIdosoReport
        exclude = ("id", "directorate", "created_by", "status", "created_at", "updated_at")

    section_map = [
        (
            "PAEFI - Familias em Acompanhamento",
            ["paefi_novos_casos", "paefi_acomp_inicio", "paefi_inseridos", "paefi_desligados",
             "paefi_bolsa_familia", "paefi_bpc", "paefi_substancias"],
        )
    ] + [
        (f"{label} (Idoso)", [f"{pref}_{suf}" for suf in ["atendidas_anterior", "inseridos", "desligados", "total"]])
        for pref, label in VICTIM_PREFIXES
    ]

    labels = {
        "paefi_novos_casos": "Casos Novos Recebidos",
        "paefi_acomp_inicio": "Familias em Acomp. 1o Dia Mes",
        "paefi_inseridos": "Familias Inseridos/Atend.",
        "paefi_desligados": "Num de Casos Desligados",
        "paefi_bolsa_familia": "Familias Benef. Bolsa Familia",
        "paefi_bpc": "Familias com BPC",
        "paefi_substancias": "Familias com Dep. Substancias",
        **{
            f"{pref}_atendidas_anterior": f"{label} - Atendidas no mes anterior"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"{pref}_inseridos": f"{label} - Inseridos / Novos"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"{pref}_desligados": f"{label} - Desligados no PAEFI"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"{pref}_total": f"{label} - Total"
            for pref, label in VICTIM_PREFIXES
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name.endswith("_total"):
                field.disabled = True
                field.widget.attrs["readonly"] = True

    def clean(self):
        cleaned = super().clean()
        for pref, _label in VICTIM_PREFIXES:
            ant = int(cleaned.get(f"def_{pref}_atendidas_anterior") or 0)
            ins = int(cleaned.get(f"def_{pref}_inseridos") or 0)
            cleaned[f"def_{pref}_total"] = ant + ins
        return cleaned
    def clean(self):
        cleaned = super().clean()
        for pref, _label in VICTIM_PREFIXES:
            ant = int(cleaned.get(f"{pref}_atendidas_anterior") or 0)
            ins = int(cleaned.get(f"{pref}_inseridos") or 0)
            cleaned[f"{pref}_total"] = ant + ins
        return cleaned


class CreasPcdForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasPcdReport
        exclude = ("id", "directorate", "created_by", "status", "created_at", "updated_at")

    section_map = [
        (f"{label} (PCD)", [f"def_{pref}_{suf}" for suf in ["atendidas_anterior", "inseridos", "desligados", "total"]])
        for pref, label in VICTIM_PREFIXES
    ]

    labels = {
        **{
            f"def_{pref}_atendidas_anterior": f"{label} - Atendidas no mes anterior"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"def_{pref}_inseridos": f"{label} - Inseridos / Novos"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"def_{pref}_desligados": f"{label} - Desligados"
            for pref, label in VICTIM_PREFIXES
        },
        **{
            f"def_{pref}_total": f"{label} - Total"
            for pref, label in VICTIM_PREFIXES
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name.endswith("_total"):
                field.disabled = True
                field.widget.attrs["readonly"] = True

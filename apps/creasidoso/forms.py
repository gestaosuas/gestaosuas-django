from django import forms
from .models import CreasIdosoReport, CreasPcdReport

MONTH_CHOICES = [(1, "JAN"), (2, "FEV"), (3, "MAR"), (4, "ABR"), (5, "MAI"), (6, "JUN"),
                  (7, "JUL"), (8, "AGO"), (9, "SET"), (10, "OUT"), (11, "NOV"), (12, "DEZ")]

IDOSO_VIOLATION_PREFIXES = [
    ("violencia_fisica", "Pessoas idosas vítimas de violência física ou psicológica"),
    ("abuso_sexual", "Pessoas idosas vítimas de abuso sexual"),
    ("exploracao_sexual", "Pessoas idosas vítimas de exploração sexual"),
    ("negligencia", "Pessoas idosas vítimas de negligência ou abandono"),
    ("exploracao_financeira", "Pessoas idosas vítimas de exploração financeira"),
]

PCD_VIOLATION_PREFIXES = [
    ("violencia_fisica", "Violência Física ou Psicológica"),
    ("abuso_sexual", "Abuso Sexual"),
    ("exploracao_sexual", "Exploração Sexual"),
    ("negligencia", "Negligência ou Abandono"),
    ("exploracao_financeira", "Exploração Financeira"),
]

IDOSO_SUFFIXES = [
    ("atendidas_anterior", "Mês Anterior"),
    ("inseridos", "Inseridos / Novos"),
    ("desligados", "Desligados no Mês"),
    ("total", "Total"),
]

PCD_SUFFIXES = [
    ("atendidas_anterior", "Mês Anterior"),
    ("inseridos", "Inseridos(as) no Mês"),
    ("desligados", "Desligados(as) no Mês"),
    ("total", "Total"),
]


class CreasIdosoForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasIdosoReport
        exclude = ("id", "directorate", "created_by", "status", "created_at", "updated_at",
                   "idoso_total_geral_masc", "idoso_total_geral_fem")

    section_map = None
    labels = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name.endswith("_total_masc") or name.endswith("_total_fem") or name.endswith("_total_geral") or name == "paefi_total_acompanhamento":
                field.disabled = True
                field.widget.attrs["readonly"] = True

        # Build section_map dynamically
        self.section_map = [
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
            self.section_map.append((label, fields))

        # Build labels dynamically
        self.labels = {
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
                self.labels[f"{pref}_{suf}_masc"] = f"{suf_label} — Masculino"
                self.labels[f"{pref}_{suf}_fem"] = f"{suf_label} — Feminino"
            self.labels[f"{pref}_total_geral"] = "Total Geral"

        # Apply labels to actual form fields
        for name, lbl in self.labels.items():
            if name in self.fields:
                self.fields[name].label = lbl

    def clean(self):
        cleaned = super().clean()
        for pref, _label in IDOSO_VIOLATION_PREFIXES:
            geral = 0
            for g in ["masc", "fem"]:
                ant = int(cleaned.get(f"{pref}_atendidas_anterior_{g}") or 0)
                ins = int(cleaned.get(f"{pref}_inseridos_{g}") or 0)
                cleaned[f"{pref}_total_{g}"] = ant + ins
                geral += ant + ins
            cleaned[f"{pref}_total_geral"] = geral
        # PAEFI total
        inicio = int(cleaned.get("paefi_acomp_inicio") or 0)
        inseridos = int(cleaned.get("paefi_inseridos") or 0)
        cleaned["paefi_total_acompanhamento"] = inicio + inseridos
        # Grand totals
        total_masc = sum(int(cleaned.get(f"{pref}_total_masc") or 0) for pref, _ in IDOSO_VIOLATION_PREFIXES)
        total_fem = sum(int(cleaned.get(f"{pref}_total_fem") or 0) for pref, _ in IDOSO_VIOLATION_PREFIXES)
        cleaned["idoso_total_geral_masc"] = total_masc
        cleaned["idoso_total_geral_fem"] = total_fem
        return cleaned


class CreasPcdForm(forms.ModelForm):
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))
    year = forms.IntegerField(label="Ano", widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020}))

    class Meta:
        model = CreasPcdReport
        exclude = ("id", "directorate", "created_by", "status", "created_at", "updated_at",
                   "def_total_geral_masc", "def_total_geral_fem")

    section_map = None
    labels = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"month", "year"}:
                continue
            field.widget = forms.NumberInput(attrs={"class": "form-input", "min": 0})
            field.required = False
            field.initial = field.initial or 0
            if name.endswith("_total_masc") or name.endswith("_total_fem"):
                field.disabled = True
                field.widget.attrs["readonly"] = True

        # Build section_map dynamically
        self.section_map = []
        for pref, label in PCD_VIOLATION_PREFIXES:
            fields = []
            for suf, _suf_label in PCD_SUFFIXES:
                fields.append(f"def_{pref}_{suf}_masc")
                fields.append(f"def_{pref}_{suf}_fem")
            self.section_map.append((f"{label} (Pessoa com Deficiência)", fields))

        # Build labels dynamically
        self.labels = {}
        for pref, label in PCD_VIOLATION_PREFIXES:
            for suf, suf_label in PCD_SUFFIXES:
                self.labels[f"def_{pref}_{suf}_masc"] = f"{suf_label} (Masculino)"
                self.labels[f"def_{pref}_{suf}_fem"] = f"{suf_label} (Feminino)"

        # Apply labels to actual form fields
        for name, lbl in self.labels.items():
            if name in self.fields:
                self.fields[name].label = lbl

    def clean(self):
        cleaned = super().clean()
        for pref, _label in PCD_VIOLATION_PREFIXES:
            for g in ["masc", "fem"]:
                ant = int(cleaned.get(f"def_{pref}_atendidas_anterior_{g}") or 0)
                ins = int(cleaned.get(f"def_{pref}_inseridos_{g}") or 0)
                cleaned[f"def_{pref}_total_{g}"] = ant + ins
        # Total geral
        for g in ["masc", "fem"]:
            total = 0
            for pref, _label in PCD_VIOLATION_PREFIXES:
                total += int(cleaned.get(f"def_{pref}_total_{g}") or 0)
            cleaned[f"def_total_geral_{g}"] = total
        return cleaned

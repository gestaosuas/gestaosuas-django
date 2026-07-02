from django import forms
from django.utils import timezone
from .models import PopRuaReport

class PopRuaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force current year if not provided
        if not self.instance.pk and not self.initial.get("year"):
            self.initial["year"] = timezone.now().year
            
        # If it's a bound form (POST) and year is empty, set it
        if self.is_bound and not self.data.get("year"):
            # This is tricky since self.data is immutable, but we can handle it in the view
            pass

        # Add form-input class to all fields and make them optional for legacy compatibility
        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-input"})
            if field_name not in ["month", "year"]:
                field.required = False

    class Meta:
        model = PopRuaReport
        exclude = ["id", "directorate", "status", "created_at", "updated_at", "created_by"]
        widgets = {
            "month": forms.Select(choices=[
                (1, "JAN."), (2, "FEV."), (3, "MAR."), (4, "ABR."),
                (5, "MAI."), (6, "JUN."), (7, "JUL."), (8, "AGO."),
                (9, "SET."), (10, "OUT."), (11, "NOV."), (12, "DEZ.")
            ]),
            "year": forms.NumberInput(attrs={"min": 2020, "max": 2030}),
        }

    section_map = [
        ("Número de Atendimentos", [
            "num_atend_centro_ref", "num_atend_abordagem", "num_atend_migracao", "num_atend_total"
        ]),
        ("Centro de Referência", [
            "cr_a1_masc", "cr_a1_fem", "cr_b1_drogas", "cr_b2_migrantes", "cr_b3_mental",
            "cr_cad_unico", "cr_enc_mercado", "cr_enc_caps", "cr_enc_saude", 
            "cr_enc_consultorio", "cr_segunda_via"
        ]),
        ("Abordagem de Rua", [
            "ar_e1_masc", "ar_e2_fem", "ar_e5_drogas", "ar_e6_migrantes", 
            "ar_persistentes", "ar_enc_centro_ref", "ar_recusa_identificacao"
        ]),
        ("Núcleo do Migrante", [
            "nm_total_passagens", "nm_passagens_deferidas", "nm_passagens_indeferidas",
            "nm_estrangeiros", "nm_retorno_familiar", "nm_busca_trabalho", "nm_busca_saude"
        ]),
    ]

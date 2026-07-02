from django import forms
from .models import CasaDaMulherReport, DiversidadeReport, NucleoDiversidadeReport

class CasaDaMulherForm(forms.ModelForm):
    month = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )
    year = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )

    section_map = [
        ("ATENDIMENTOS", ["cm_atend_mulheres_atendidas"]),
        ("FAIXA ETÁRIA QTD", [
            "cm_faixa_16_17", "cm_faixa_18_30", "cm_faixa_31_40", 
            "cm_faixa_41_50", "cm_faixa_51_60", "cm_faixa_acima_60", "cm_faixa_nao_consta"
        ]),
        ("COR/RAÇA", [
            "cm_raca_branca", "cm_raca_preta", "cm_raca_parda", 
            "cm_raca_amarelo", "cm_raca_indigena", "cm_raca_nao_consta"
        ]),
        ("TIPO DE VIOLÊNCIA", [
            "cm_violencia_fisica", "cm_violencia_moral", "cm_violencia_psicologica", 
            "cm_violencia_sexual", "cm_violencia_patrimonial", "cm_violencia_nenhuma", "cm_violencia_outras"
        ]),
        ("ENCAMINHAMENTOS", [
            "cm_encam_bo_ocorrencia", "cm_encam_casa_abrigo", "cm_encam_conselho_idoso", 
            "cm_encam_conselho_tutelar", "cm_encam_defens_publica", "cm_encam_forum_juizados", 
            "cm_encam_exame_c_delito", "cm_encam_deam", "cm_encam_ministerio_publico", 
            "cm_encam_outra_delegacia", "cm_encam_ppvd", "cm_encam_rede_ass_social", 
            "cm_encam_rede_saude", "cm_encam_sine", "cm_encam_outros"
        ]),
    ]

    labels = {
        "cm_atend_mulheres_atendidas": "Mulheres Atendidas",
        
        "cm_faixa_16_17": "16 à 17 anos",
        "cm_faixa_18_30": "18 à 30 anos",
        "cm_faixa_31_40": "31 à 40 anos",
        "cm_faixa_41_50": "41 à 50 anos",
        "cm_faixa_51_60": "51 à 60 anos",
        "cm_faixa_acima_60": "Acima de 60",
        "cm_faixa_nao_consta": "Não Consta (Faixa)",
        
        "cm_raca_branca": "Branca",
        "cm_raca_preta": "Preta",
        "cm_raca_parda": "Parda",
        "cm_raca_amarelo": "Amarela",
        "cm_raca_indigena": "Indígena",
        "cm_raca_nao_consta": "Não Consta (Raça)",
        
        "cm_violencia_fisica": "Física",
        "cm_violencia_moral": "Moral",
        "cm_violencia_psicologica": "Psicológica",
        "cm_violencia_sexual": "Sexual",
        "cm_violencia_patrimonial": "Patrimonial",
        "cm_violencia_nenhuma": "Nenhuma Agressão física",
        "cm_violencia_outras": "Outras",
        
        "cm_encam_bo_ocorrencia": "Boletim de Ocorrência",
        "cm_encam_casa_abrigo": "Casa Abrigo",
        "cm_encam_conselho_idoso": "Conselho do Idoso",
        "cm_encam_conselho_tutelar": "Conselho Tutelar",
        "cm_encam_defens_publica": "Defensoria Pública",
        "cm_encam_forum_juizados": "Fórum/Juizados",
        "cm_encam_exame_c_delito": "Exame Corpo de Delito",
        "cm_encam_deam": "DEAM",
        "cm_encam_ministerio_publico": "Ministério Público",
        "cm_encam_outra_delegacia": "Outra Delegacia",
        "cm_encam_ppvd": "PPVD",
        "cm_encam_rede_ass_social": "Rede de Assistência Social",
        "cm_encam_rede_saude": "Rede de Saúde",
        "cm_encam_sine": "SINE",
        "cm_encam_outros": "Outros Encaminhamentos",
    }

    class Meta:
        model = CasaDaMulherReport
        exclude = ["id", "directorate", "status", "user_id", "created_by", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, label in self.labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
                self.fields[field_name].required = False
                self.fields[field_name].widget.attrs.update({
                    "class": "form-input block w-full rounded-lg border-zinc-200 focus:border-indigo-500 focus:ring focus:ring-indigo-500/20 text-sm py-2 px-3 transition-colors duration-200 dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100",
                    "min": "0"
                })


class DiversidadeForm(forms.ModelForm):
    month = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )
    year = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )

    section_map = [
        ("ATENDIMENTO", ["div_atend_mulheres_atendidas", "div_atend_nucleo_diversidade"]),
        ("FAIXA ETÁRIA", [
            "div_faixa_16_17", "div_faixa_18_30", "div_faixa_31_40", 
            "div_faixa_41_50", "div_faixa_51_60", "div_faixa_acima_60", "div_faixa_nao_consta"
        ]),
        ("COR/RAÇA", [
            "div_raca_branca", "div_raca_preta", "div_raca_parda", 
            "div_raca_amarela", "div_raca_indigena", "div_raca_nao_consta"
        ]),
        ("SITUAÇÃO DA DEMANDA", [
            "div_sit_violencia_infrafamiliar", "div_sit_violencia_extrafamiliar", "div_sit_demanda_fora_contexto"
        ]),
        ("ENCAMINHAMENTOS", [
            "div_encam_juizado", "div_encam_rede_socioassist", "div_encam_curso_prof", 
            "div_encam_sine", "div_encam_serv_saude", "div_encam_mobilizacao_familia", 
            "div_encam_orient_juridicas", "div_encam_bo_reds", "div_encam_exame_delito", "div_encam_outros"
        ]),
    ]

    labels = {
        "div_atend_mulheres_atendidas": "Pessoas Atendidas",
        "div_atend_nucleo_diversidade": "Núcleo Diversidade",
        
        "div_faixa_16_17": "16 à 17 anos",
        "div_faixa_18_30": "18 à 30 anos",
        "div_faixa_31_40": "31 à 40 anos",
        "div_faixa_41_50": "41 à 50 anos",
        "div_faixa_51_60": "51 à 60 anos",
        "div_faixa_acima_60": "Acima de 60",
        "div_faixa_nao_consta": "Não Consta (Faixa)",
        
        "div_raca_branca": "Branca",
        "div_raca_preta": "Preta",
        "div_raca_parda": "Parda",
        "div_raca_amarela": "Amarela",
        "div_raca_indigena": "Indígena",
        "div_raca_nao_consta": "Não Consta (Raça)",
        
        "div_sit_violencia_infrafamiliar": "Violência infrafamiliar que não incide Lei Maria da Penha",
        "div_sit_violencia_extrafamiliar": "Violência extrafamiliar",
        "div_sit_demanda_fora_contexto": "Demanda fora do contexto de violência",
        
        "div_encam_juizado": "Juizado Especial",
        "div_encam_rede_socioassist": "Rede Socioassistencial",
        "div_encam_curso_prof": "Curso Profissionalizante",
        "div_encam_sine": "Sine",
        "div_encam_serv_saude": "Serviços de Saúde da Rede",
        "div_encam_mobilizacao_familia": "Mobilização da família extensa ou ampliada do usuário",
        "div_encam_orient_juridicas": "Orientações Jurídicas",
        "div_encam_bo_reds": "Registro BO/REDS",
        "div_encam_exame_delito": "Exame de Corpo de Delito",
        "div_encam_outros": "Outros",
    }

    class Meta:
        model = DiversidadeReport
        exclude = ["id", "directorate", "status", "user_id", "created_by", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, label in self.labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
                self.fields[field_name].required = False
                self.fields[field_name].widget.attrs.update({
                    "class": "form-input block w-full rounded-lg border-zinc-200 focus:border-indigo-500 focus:ring focus:ring-indigo-500/20 text-sm py-2 px-3 transition-colors duration-200 dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100",
                    "min": "0"
                })


class NucleoDiversidadeForm(forms.ModelForm):
    month = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )
    year = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )

    section_map = [
        ("ATENDIMENTOS", ["nd_pessoas_atendidas"]),
    ]

    labels = {
        "nd_pessoas_atendidas": "Pessoas Atendidas",
    }

    class Meta:
        model = NucleoDiversidadeReport
        exclude = ["id", "directorate", "status", "user_id", "created_by", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, label in self.labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
                self.fields[field_name].required = False
                self.fields[field_name].widget.attrs.update({
                    "class": "form-input block w-full rounded-lg border-zinc-200 focus:border-indigo-500 focus:ring focus:ring-indigo-500/20 text-sm py-2 px-3 transition-colors duration-200 dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100",
                    "min": "0"
                })

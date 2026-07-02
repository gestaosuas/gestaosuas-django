from django import forms
from apps.core.forms import StyledMonitoringForm
from .models import SineReport, QualificacaoReport


class SineReportForm(StyledMonitoringForm):
    class Meta:
        model = SineReport
        exclude = ("id", "directorate", "user_external_id", "created_at", "updated_at")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input", "min": 2020}),
        }

    section_map = [
        (
            "INDICADORES MENSAIS",
            [
                "atend_trabalhador",
                "atend_online_trabalhador",
                "atend_empregador",
                "atend_online_empregador",
                "seguro_desemprego",
                "vagas_captadas",
                "ligacoes_recebidas",
                "ligacoes_realizadas",
                "curriculos",
                "entrevistados",
                "proc_administrativos",
                "processo_seletivo",
                "inseridos_mercado",
                "carteira_digital",
                "orientacao_profissional",
                "convocacao_trabalhadores",
                "vagas_alto_valor",
                "atendimentos",
            ],
        )
    ]

    labels = {
        "atend_trabalhador": "Atendimento ao Trabalhador",
        "atend_online_trabalhador": "Atendimento online ao Trabalhador",
        "atend_empregador": "Atendimento ao Empregador",
        "atend_online_empregador": "Atendimento online ao Empregador",
        "seguro_desemprego": "Seguro desemprego",
        "vagas_captadas": "Vagas captadas",
        "ligacoes_recebidas": "Numero de ligacoes recebidas",
        "ligacoes_realizadas": "Numero de ligacoes realizadas",
        "curriculos": "Curriculos",
        "entrevistados": "Entrevistados",
        "proc_administrativos": "Primeiro Emprego",
        "processo_seletivo": "Processo seletivo",
        "inseridos_mercado": "Inseridos no mercado de trabalho",
        "carteira_digital": "Carteira digital de trabalho",
        "orientacao_profissional": "Orientacao Profissional",
        "convocacao_trabalhadores": "Convocacao Trabalhadores",
        "vagas_alto_valor": "Vagas de alto valor agregado",
        "atendimentos": "Atendimentos",
    }


class QualificacaoReportForm(StyledMonitoringForm):
    class Meta:
        model = QualificacaoReport
        exclude = ("id", "directorate", "user_external_id", "created_at", "updated_at")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input", "min": 2020}),
        }

    section_map = [
        (
            "RESUMO CP",
            [
                "resumo_vagas",
                "resumo_cursos",
                "resumo_turmas",
                "resumo_concluintes",
                "resumo_mulheres",
                "resumo_homens",
                "resumo_mercado_fem",
                "resumo_mercado_masc",
                "resumo_vagas_ocupadas",
                "resumo_taxa_ocupacao",
            ],
        ),
        (
            "CONCLUINTES",
            [
                "cp_morumbi_concluintes",
                "cp_lagoinha_concluintes",
                "cp_campo_alegre_concluintes",
                "cp_luizote_1_concluintes",
                "cp_luizote_2_concluintes",
                "cp_tocantins_concluintes",
                "cp_planalto_concluintes",
                "onibus_concluintes_unit",
                "maravilha_concluintes",
                "uditech_concluintes",
            ],
        ),
        (
            "ONIBUS MEU OFICIO",
            [
                "bairros_visitados",
                "concluintes_onibus",
                "cursos_onibus",
            ],
        ),
        (
            "ATENDIMENTOS",
            [
                "cp_morumbi_atendimentos",
                "cp_lagoinha_atendimentos",
                "cp_campo_alegre_atendimentos",
                "cp_luizote_1_atendimentos",
                "cp_luizote_2_atendimentos",
                "cp_tocantis_atendimentos",
                "cp_planalto_atendimentos",
                "maravilha_atendimentos",
                "unitech_atendimentos",
                "onibus_atendimentos",
            ],
        ),
        ("PARCERIAS E CURSOS", ["cursos_andamento"]),
    ]

    labels = {
        "resumo_vagas": "Vagas oferecidas",
        "resumo_cursos": "Cursos",
        "resumo_turmas": "Turmas",
        "resumo_concluintes": "Concluintes",
        "resumo_mulheres": "Mulheres",
        "resumo_homens": "Homens",
        "resumo_mercado_fem": "Inseridos no mercado de trabalho (feminino)",
        "resumo_mercado_masc": "Inseridos no mercado de trabalho (masculino)",
        "resumo_vagas_ocupadas": "Vagas ocupadas",
        "resumo_taxa_ocupacao": "Taxa de ocupacao (%)",
        "cp_morumbi_concluintes": "CP MORUMBI",
        "cp_lagoinha_concluintes": "CP LAGOINHA",
        "cp_campo_alegre_concluintes": "CP CAMPO ALEGRE",
        "cp_luizote_1_concluintes": "CP LUIZOTE I",
        "cp_luizote_2_concluintes": "CP LUIZOTE II",
        "cp_tocantins_concluintes": "CP TOCANTINS",
        "cp_planalto_concluintes": "CP PLANALTO",
        "onibus_concluintes_unit": "ONIBUS",
        "maravilha_concluintes": "MARAVILHA",
        "uditech_concluintes": "UDITECH",
        "bairros_visitados": "Bairros Visitados",
        "concluintes_onibus": "Concluintes",
        "cursos_onibus": "Cursos",
        "cp_morumbi_atendimentos": "CP MORUMBI",
        "cp_lagoinha_atendimentos": "CP LAGOINHA",
        "cp_campo_alegre_atendimentos": "CP CAMPO ALEGRE",
        "cp_luizote_1_atendimentos": "CP LUIZOTE I",
        "cp_luizote_2_atendimentos": "CP LUIZOTE II",
        "cp_tocantis_atendimentos": "CP TOCANTIS",
        "cp_planalto_atendimentos": "CP PLANALTO",
        "maravilha_atendimentos": "MARAVILHA",
        "unitech_atendimentos": "UDITECH",
        "onibus_atendimentos": "ONIBUS",
        "cursos_andamento": "Cursos em andamento (CP)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "resumo_taxa_ocupacao" in self.fields:
            self.fields["resumo_taxa_ocupacao"].disabled = True
            self.fields["resumo_taxa_ocupacao"].widget.attrs["readonly"] = True

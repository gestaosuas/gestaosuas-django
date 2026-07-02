from django import forms
from apps.core.forms import StyledMonitoringForm
from .models import BeneficiosReport


class BeneficiosReportForm(StyledMonitoringForm):
    class Meta:
        model = BeneficiosReport
        exclude = ("id", "directorate", "user_external_id", "created_at", "updated_at")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input", "min": 2020}),
        }

    section_map = [
        (
            "SERVICOS E BENEFICIOS",
            [
                "encaminhadas_inclusao_cadunico",
                "encaminhadas_atualizacao_cadunico",
                "consulta_cadunico",
                "numero_nis",
                "dmae",
                "pro_pao",
                "auxilio_documento",
                "carteirinha_idoso",
                "bpc_presencial",
                "bpc_online",
                "solicitacao_colchoes",
                "cesta_basica",
                "solicitacao_fraldas",
                "absorvente",
                "agasalho_cobertor",
            ],
        ),
        (
            "VISITAS DOMICILIARES",
            [
                "visitas_cadunico",
                "visita_nucleo_habitacao",
                "visita_cesta_fraldas_colchoes",
                "visita_dmae",
                "visitas_pro_pao",
                "total_visitas",
            ],
        ),
        (
            "ATENDIMENTOS",
            ["busao_social_1", "busao_social_2", "dibs"],
        ),
        ("FAMILIAS BENEFICIADAS E CADASTROS", ["familias_pbf", "pessoas_cadunico"]),
    ]

    labels = {
        "encaminhadas_inclusao_cadunico": "Familias encaminhadas para inclusao CadUnico",
        "encaminhadas_atualizacao_cadunico": "Familias encaminhadas para atualizacao cadastral no CadUnico",
        "consulta_cadunico": "Consulta CadUnico",
        "numero_nis": "Numero NIS",
        "dmae": "DMAE (Deferidos)",
        "pro_pao": "Pro-pao (Cestas entregues)",
        "auxilio_documento": "Auxilio Documento",
        "carteirinha_idoso": "Carteirinha do Idoso",
        "bpc_presencial": "BPC Presencial",
        "bpc_online": "BPC Online",
        "solicitacao_colchoes": "Solicitacao de Colchoes",
        "cesta_basica": "Cesta Basica (Entregues)",
        "solicitacao_fraldas": "Solicitacao de fraldas",
        "absorvente": "Absorvente",
        "agasalho_cobertor": "Agasalho / cobertor",
        "visitas_cadunico": "Visitas CadUnico",
        "visita_nucleo_habitacao": "Visita Nucleo S. Habitacao",
        "visita_cesta_fraldas_colchoes": "Visita Cesta Basica / Fraldas / Colchoes",
        "visita_dmae": "Visita DMAE",
        "visitas_pro_pao": "Visitas Pro-pao",
        "total_visitas": "Total de visita",
        "busao_social_1": "Busao Social 1",
        "busao_social_2": "Busao Social 2",
        "dibs": "DIBS",
        "familias_pbf": "Familias beneficiadas no PBF",
        "pessoas_cadunico": "Pessoas cadastradas no CadUnico",
    }

    help_texts = {
        "auxilio_documento": "Soma de certidao de nascimento, casamento e obito.",
    }

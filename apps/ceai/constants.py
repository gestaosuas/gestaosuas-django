CEAI_UNITS = [
    "Brasil",
    "Laranjeiras",
    "Luizote",
    "Guarani",
    "Morumbi"
]

CEAI_FORM_DEFINITION = {
    "sections": [
        {
            "title": "Atendimentos e Movimentação",
            "fields": [
                { "id": "atendidos_anterior_masc", "label": "Matriculados no 1º dia do Mês (Masc)", "type": "number" },
                { "id": "atendidos_anterior_fem", "label": "Matriculados no 1º dia do Mês (Fem)", "type": "number" },
                { "id": "inseridos_masc", "label": "Inseridos no mês (Masc)", "type": "number" },
                { "id": "inseridos_fem", "label": "Inseridos no mês (Fem)", "type": "number" },
                { "id": "desligados_masc", "label": "Desligados (Masc)", "type": "number" },
                { "id": "desligados_fem", "label": "Desligados (Fem)", "type": "number" },
                { "id": "total_inseridos", "label": "Total de Idosos Atendidos (ano)", "type": "number", "disabled": True },
                { "id": "total_atendimentos", "label": "Atendimentos", "type": "number" }
            ]
        }
    ]
}

CONDOMINIO_IDOSO_FORM_DEFINITION = {
    "sections": [
        {
            "title": "Laranjeiras",
            "fields": [
                { "id": "lar_moradores_fem", "label": "Moradores Fem", "type": "number" },
                { "id": "lar_moradores_masc", "label": "Moradores Masc", "type": "number" }
            ]
        },
        {
            "title": "Guarani",
            "fields": [
                { "id": "gua_moradores_fem", "label": "Moradores Fem", "type": "number" },
                { "id": "gua_moradores_masc", "label": "Moradores Masc", "type": "number" }
            ]
        }
    ]
}

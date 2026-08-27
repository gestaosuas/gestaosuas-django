"""Construtores de PDF (ReportLab) especificos do modulo de monitoramento
(Subvencao/Emendas): Documento de Visita, Documento do Plano de Trabalho e
Relatorio/Parecer de Visita. Ver apps/core/pdf.py para as primitivas
compartilhadas; o Relatorio Mensal Narrativo fica em
apps/core/pdf.py:render_narrative_report_pdf por ser usado por 9 apps.
"""
import html

from reportlab.platypus import Paragraph, Spacer

from apps.core import pdf as pdfmod

_QUANT_MONTHS = [
    ("jan", "JAN"), ("fev", "FEV"), ("mar", "MAR"), ("abr", "ABR"),
    ("mai", "MAI"), ("jun", "JUN"), ("jul", "JUL"), ("ago", "AGO"),
    ("set", "SET"), ("out", "OUT"), ("nov", "NOV"), ("dez", "DEZ"),
]


_ATENDIMENTO_QUANT_LABELS = [
    ("usuarios_primeiro_dia", "Total de usuários do serviço no 1º dia do mês"),
    ("usuarios_inseridos", "Total de usuários inseridos no mês (novos)"),
    ("usuarios_desligados", "Total de usuários desligados no mês"),
    ("usuarios_ultimo_dia", "Total de usuários do serviço no último dia do mês"),
]


def _atendimento_quant_table(pse_quantitativos, styles):
    rows = []
    for key, label in _ATENDIMENTO_QUANT_LABELS:
        month_values = (pse_quantitativos or {}).get(key) or {}
        rows.append([label] + [month_values.get(m, "-") or "-" for m, _ in _QUANT_MONTHS])
    headers = ["Indicador"] + [label for _, label in _QUANT_MONTHS]
    col_widths = [55 * pdfmod.mm] + [None] * 12
    return pdfmod.styled_table(headers, rows, styles, col_widths=col_widths)


def _format_address(osc):
    parts = [osc.address or "Nao informado"]
    if osc.number:
        parts.append(f", {osc.number}")
    if osc.neighborhood:
        parts.append(f" - {osc.neighborhood}")
    return "".join(parts)


def render_work_plan_document_pdf(context):
    styles = pdfmod.build_styles()
    osc = context["osc"]
    directorate = context["directorate"]
    document_title = context["document_title"]
    content_blocks = context["content_blocks"]

    story = []

    osc_rows = [
        ("Nome", osc.name),
        ("Atividade", osc.activity_type or "Nao informada"),
        ("Endereco", _format_address(osc)),
        ("Telefone", osc.phone or "Nao informado"),
        ("Subvencionados", osc.subsidized_count or 0),
        ("Diretoria", directorate.name),
    ]
    osc_table = pdfmod.styled_table(["Campo", "Valor"], osc_rows, styles, col_widths=[45 * pdfmod.mm, None])
    story.extend(pdfmod.heading_with_body(
        Paragraph("I. Dados da Organizacao da Sociedade Civil - OSC", styles["h2"]), osc_table,
    ))

    partnership_fields = [
        (label, value) for label, value in (
            ("Objeto", osc.objeto), ("Objetivos", osc.objetivos),
            ("Metas", osc.metas), ("Atividades", osc.atividades),
        ) if value
    ]
    if partnership_fields:
        first_label, first_value = partnership_fields[0]
        story.extend(pdfmod.heading_with_body(
            Paragraph("II. Informacoes da Parceria", styles["h2"]),
            Paragraph(first_label, styles["h3"]), Paragraph(first_value, styles["body"]),
        ))
        for label, value in partnership_fields[1:]:
            story.extend(pdfmod.heading_with_body(Paragraph(label, styles["h3"]), Paragraph(value, styles["body"])))

    block_flowables = []
    for block in content_blocks:
        block_type = block.get("type")
        content = block.get("content")
        if block_type == "title":
            block_flowables.append(Paragraph(str(content or ""), styles["h3"]))
        elif block_type == "table" and isinstance(content, dict) and content.get("headers"):
            block_flowables.append(pdfmod.styled_table(content["headers"], content.get("rows", []), styles))
        elif block_type == "table":
            block_flowables.append(Paragraph("Esta tabela ainda nao possui dados definidos.", styles["body_empty"]))
        else:
            for para in str(content or "").split("\n"):
                if para.strip():
                    block_flowables.append(Paragraph(para.strip(), styles["body"]))

    section_heading = Paragraph("III. Conteudo Estruturado do Plano", styles["h2"])
    if not block_flowables:
        story.extend(pdfmod.heading_with_body(
            section_heading, Paragraph("Este plano ainda nao possui conteudo estruturado.", styles["body_empty"]),
        ))
    else:
        glued_blocks = pdfmod.glue_headings(block_flowables, styles)
        story.extend(pdfmod.heading_with_body(section_heading, glued_blocks[0]))
        story.extend(glued_blocks[1:])

    filename = f"plano-de-trabalho-{osc.name}.pdf".replace(" ", "-")
    return pdfmod.pdf_response(document_title, f"{directorate.name} - Plano de Trabalho", story, filename)


def render_visit_document_pdf(context):
    styles = pdfmod.build_styles()
    visit = context["object"]
    osc = visit.osc
    directorate = context["directorate"]
    extra_visits = context.get("extra_visits", [])
    is_subvencao_visit = context.get("is_subvencao_visit")
    is_emendas_visit = context.get("is_emendas_visit")
    identificacao = visit.identificacao or {}
    atendimento = visit.atendimento or {}
    assinaturas = visit.assinaturas or {}

    story = []

    # I. Identificação da OSC e da Visita
    visit_date_str = visit.visit_date.strftime("%d/%m/%Y") if visit.visit_date else "-"
    shift = identificacao.get("visit_shift_1")
    date_cell = visit_date_str + (f" - Turno: {shift.title()}" if shift else "")
    id_rows = [
        ("Instituição (OSC)", osc.name),
        ("Atividade / Natureza", osc.activity_type or "Não informada"),
        ("Endereço", _format_address(osc)),
        ("Telefone", osc.phone or "---"),
        ("Data da Visita", date_cell),
    ]
    for ev in extra_visits:
        cell = (ev.get("date") or "") + (f" - Turno: {ev['shift'].title()}" if ev.get("shift") else "")
        id_rows.append((f"{ev['num']}ª Visita", cell))
    id_table = pdfmod.styled_table(["Campo", "Valor"], id_rows, styles, col_widths=[45 * pdfmod.mm, None])
    story.extend(pdfmod.heading_with_body(Paragraph("I. Identificação da OSC e da Visita", styles["h2"]), id_table))

    # II. Dados de Atendimento
    if atendimento.get("tipo_horario") == "24h":
        horario = "Atendimento 24 Horas"
    else:
        horario = f"{atendimento.get('horario_inicio') or '--:--'} às {atendimento.get('horario_fim') or '--:--'}"
    presentes = atendimento.get("presentes") or {}
    presencas = f"Manhã: {presentes.get('manha', 0)} | Tarde: {presentes.get('tarde', 0)} | Total: {presentes.get('total', 0)}"
    subsidized = osc.subsidized_count
    capacidade = "Conforme Demanda" if subsidized == -1 else f"{subsidized or 0} usuários"
    grid_rows = [
        ("Horário de Funcionamento", horario),
        ("Usuários Presentes", presencas),
        ("Total / Mês", atendimento.get("total_mes", 0)),
    ]
    if atendimento.get("lista_espera") == "sim":
        grid_rows.append(("Lista de Espera", f"{atendimento.get('lista_espera_quantidade', 0)} pessoas"))
    grid_rows.append(("Capacidade Subvencionada", capacidade))
    grid_table = pdfmod.styled_table(
        ["Campo", "Valor"],
        grid_rows,
        styles, col_widths=[55 * pdfmod.mm, None],
    )
    body_blocks = [grid_table]
    if is_subvencao_visit and not is_emendas_visit:
        body_blocks.append(Paragraph("Atividades Desenvolvidas", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("atividades_momento") or "Nenhuma atividade descrita.", styles["body"]))
        body_blocks.append(Paragraph("Atividades em Execução no Momento", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("atividades_execucao") or "Nenhuma atividade descrita.", styles["body"]))
    elif is_emendas_visit:
        body_blocks.append(Paragraph("Aplicação do Recurso, Conforme Objeto Estabelecido e Prestação de Contas", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("aplicacao_recurso") or "Não informado.", styles["body"]))
        body_blocks.append(Paragraph("Resultados da Aplicação dos Recursos no Atendimento", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("resultados_recursos") or "Não informado.", styles["body"]))
        body_blocks.append(Paragraph("Itens Identificados no Momento da Visita Técnica", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("itens_identificados") or "Não informado.", styles["body"]))
        body_blocks.append(Paragraph("Itens Não Identificados na OSC", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("itens_nao_identificados") or "Não informado.", styles["body"]))
        body_blocks.append(Paragraph("Observações", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("observacoes_atendimento") or "Sem observações registradas.", styles["body"]))
        body_blocks.append(Paragraph("Recomendações", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("recomendacoes_atendimento") or "Sem recomendações registradas.", styles["body"]))
    else:
        body_blocks.append(Paragraph("Aplicação do Recurso e Prestação de Contas", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("aplicacao_recurso") or "Não informado.", styles["body"]))
        body_blocks.append(Paragraph("Resultados da Aplicação dos Recursos", styles["h3"]))
        body_blocks.append(Paragraph(atendimento.get("resultados_recursos") or "Não informado.", styles["body"]))
    body_blocks = pdfmod.glue_headings(body_blocks, styles)
    story.extend(pdfmod.heading_with_body(Paragraph("II. Dados de Atendimento", styles["h2"]), body_blocks[0]))
    story.extend(body_blocks[1:])

    if not is_emendas_visit:
        # III. Colaboradores / Recursos Humanos
        rh_rows = [
            [
                row.get("cargo", ""),
                "Sim" if row.get("terceirizado") else "Não",
                "Sim" if row.get("outros") else "Não",
                "Sim" if row.get("subvencao") else "Não",
                row.get("quantidade", 0),
                row.get("observacoes", "") or "-",
            ]
            for row in (visit.rh_data or [])
            if any([row.get("cargo"), row.get("observacoes"), row.get("quantidade"),
                    row.get("terceirizado"), row.get("outros"), row.get("subvencao")])
        ]
        if not rh_rows:
            rh_rows = [["Nenhum colaborador registrado.", "", "", "", "", ""]]
        rh_table = pdfmod.styled_table(
            ["Cargo / Função", "Terceirizado", "Outros", "Subvenção", "Qtd.", "Nomes / Observações"], rh_rows, styles,
        )
        rh_title = "III. Colaboradores" if is_subvencao_visit else "III. Recursos Humanos"
        story.extend(pdfmod.heading_with_body(Paragraph(rh_title, styles["h2"]), rh_table))

        # IV. Observações e Recomendações Técnicas
        obs_blocks = pdfmod.glue_headings([
            Paragraph("Parecer da Equipe Técnica", styles["h3"]),
            Paragraph(visit.observacoes or "Sem observações registradas.", styles["body"]),
            Paragraph("Recomendações e Encaminhamentos", styles["h3"]),
            Paragraph(visit.recomendacoes or "Sem recomendações registradas.", styles["body"]),
        ], styles)
        story.extend(pdfmod.heading_with_body(Paragraph("IV. Observações e Recomendações Técnicas", styles["h2"]), obs_blocks[0]))
        story.extend(obs_blocks[1:])

    # V. Dados PSE (Proteção Social Especial) -- so quando habilitado, so Subvencao
    if is_subvencao_visit and atendimento.get("pse_habilitado") == "sim":
        pse_blocks = [Paragraph(f"Período: {atendimento.get('pse_periodo') or 'Não informado'}", styles["body"])]
        qualitativos = [
            row for row in (atendimento.get("pse_qualitativos") or [])
            if any(row.get(k) for k in ("data", "situacao", "recomendacoes", "observacao"))
        ]
        if qualitativos:
            pse_rows = [
                [row.get("data", "---"), row.get("situacao", "---"), row.get("recomendacoes", "---"), row.get("observacao", "---")]
                for row in qualitativos
            ]
            pse_blocks.append(pdfmod.styled_table(["Data", "Situação Encontrada", "Recomendações", "Observação"], pse_rows, styles))
        if atendimento.get("pse_quantitativos"):
            pse_blocks.append(Paragraph("Quantitativos (Trimestral)", styles["h3"]))
            pse_blocks.append(_atendimento_quant_table(atendimento.get("pse_quantitativos"), styles))
        story.extend(pdfmod.heading_with_body(Paragraph("V. Dados PSE (Proteção Social Especial)", styles["h2"]), pse_blocks[0]))
        story.extend(pse_blocks[1:])

    # Balanço Financeiro
    balances = [doc for doc in (visit.documents or []) if doc.get("type") == "Balanço Financeiro"]
    if balances:
        story.append(Paragraph("Balanço Financeiro", styles["h2"]))
        for doc in balances:
            name = html.escape(doc.get("name") or "Arquivo PDF")
            url = html.escape(doc.get("url") or "", quote=True)
            story.append(Paragraph(f'<link href="{url}" color="#1e40af">{name}</link>', styles["body"]))

    # Fotos / Evidências
    photos = [doc for doc in (visit.documents or []) if doc.get("type") == "Foto / Evidência"]
    if photos:
        story.append(Paragraph("Fotos / Evidências", styles["h2"]))
        story.append(pdfmod.photo_grid(photos, styles))

    # Assinaturas -- ancoradas no rodape da ultima pagina
    signatures = []
    if assinaturas.get("tecnico1"):
        signatures.append({"label": "Técnico de Monitoramento", "name": assinaturas.get("tecnico1_nome") or "Técnico Responsável 1", "image": assinaturas.get("tecnico1")})
    if assinaturas.get("tecnico2"):
        signatures.append({"label": "Técnico de Monitoramento", "name": assinaturas.get("tecnico2_nome") or "Técnico Responsável 2", "image": assinaturas.get("tecnico2")})
    if assinaturas.get("responsavel"):
        signatures.append({"label": "Representante da Instituição", "name": assinaturas.get("responsavel_nome") or "Representante da OSC", "image": assinaturas.get("responsavel")})
    if signatures:
        story.append(pdfmod.signature_block(signatures, styles))

    filename = f"visita-{osc.name}-{visit.visit_date}.pdf".replace(" ", "-")
    return pdfmod.pdf_response(
        "Relatório de Visita Técnica de Monitoramento",
        f"{directorate.name} - {osc.name}",
        story, filename,
    )


def _get_reference_year():
    try:
        from apps.core.models import SystemSetting
        setting = SystemSetting.objects.filter(key="system_reference_year").first()
        if setting and setting.value:
            return setting.value
    except Exception:
        pass
    return "2026"


def _partnership_data_table(report_data, is_subvencao, styles, valor_label="Valor autorizado por lei e repassado", anotacoes=None):
    rows = [
        ("CNPJ", report_data.get("cnpj") or "-"),
    ]
    if not is_subvencao:
        rows.append(("Recurso", report_data.get("emenda") or "-"))
    rows.append(("Nº Termo", report_data.get("termo_fomento") or "-"))
    rows.append(("Vigência", report_data.get("vigencia") or "-"))
    rows.append((valor_label, report_data.get("valor_autorizado") or "-"))
    if anotacoes:
        rows.append(("Anotações", anotacoes))
    return pdfmod.styled_table(["Campo", "Valor"], rows, styles, col_widths=[60 * pdfmod.mm, None])


def _signature_pair(report_data, key_a, name_a, label_a, key_b, name_b, label_b):
    signatures = []
    if report_data.get(key_a):
        signatures.append({"label": label_a, "name": report_data.get(name_a) or "Não identificado", "image": report_data.get(key_a)})
    if report_data.get(key_b):
        signatures.append({"label": label_b, "name": report_data.get(name_b) or "Não identificado", "image": report_data.get(key_b)})
    return signatures


def _cumprimento_narrativa(report_data, osc_name, is_subvencao, is_emendas):
    """Porta a logica de updateNarrativeText() (report_form.html) pro
    servidor -- esse texto so existe hoje gerado em JS no navegador, nunca
    persistido, entao o PDF precisa recalcula-lo a partir de item4_type/
    item4_custom (unicos campos realmente salvos)."""
    term_text = "Termo de Fomento" if report_data.get("term_type") == "fomento" else "Termo de Colaboração"
    execution_verb = "foi executada" if is_emendas else "está sendo executada"
    date_suffix = "" if (is_subvencao or is_emendas) else " até a presente data"
    tipo = report_data.get("item4_type")

    if tipo == "fully":
        narrativa = (
            f"constatou-se que a parceria com a entidade {osc_name} {execution_verb} de maneira coerente "
            f"com o Plano de Trabalho – Anexo I parte integrante do {term_text}, desenvolvendo as atividades "
            "e atingindo tanto os objetivos quanto as metas qualitativas e quantitativas estabelecidas, "
            "logo, cumprindo o objeto pactuado."
        )
    elif tipo in ("partially", "partially_quant"):
        narrativa = (
            f"constatou-se que a parceria com a entidade {osc_name} {execution_verb} de maneira coerente "
            f"com o Plano de Trabalho – Anexo I parte integrante do {term_text} no que se refere ao "
            "desenvolvimento das atividades, alcance dos objetivos e metas qualitativas. Entretanto, a meta "
            f"quantitativa não foi alcançada plenamente, logo, cumprindo parcialmente o objeto pactuado{date_suffix}."
        )
    elif tipo == "partially_qual":
        narrativa = (
            f"constatou-se que a parceria com a entidade {osc_name} {execution_verb} de maneira coerente "
            f"com o Plano de Trabalho – Anexo I parte integrante do {term_text} no que se refere ao "
            "desenvolvimento das atividades, alcance dos objetivos e metas quantitativas. Entretanto, a meta "
            f"qualitativa não foi alcançada plenamente, logo, cumprindo parcialmente o objeto pactuado{date_suffix}."
        )
    elif tipo == "custom":
        custom = report_data.get("item4_custom") or "_" * 40
        narrativa = f"constatou-se que a parceria com a entidade {osc_name} {custom}"
    else:
        narrativa = ""

    return (
        "Com base nas descrições relatadas e análises realizadas do monitoramento e avaliação desenvolvido "
        f"por meio de Visita Técnica in loco, {narrativa}"
    )


def _quant_table(item5_quantitativos, styles):
    labels = [
        ("total_1dia", "Total no 1º dia do mês"),
        ("inseridos", "Usuários inseridos"),
        ("desligados", "Usuários desligados"),
        ("total_ultimo", "Total no último dia"),
    ]
    rows = []
    for key, label in labels:
        month_values = (item5_quantitativos or {}).get(key) or {}
        rows.append([label] + [month_values.get(m, "-") or "-" for m, _ in _QUANT_MONTHS])
    headers = ["Indicador"] + [label for _, label in _QUANT_MONTHS]
    col_widths = [40 * pdfmod.mm] + [None] * 12
    return pdfmod.styled_table(headers, rows, styles, col_widths=col_widths)


def render_visit_report_pdf(context):
    styles = pdfmod.build_styles()
    visit = context["visit"]
    osc = visit.osc
    directorate = context["directorate"]
    report_type = context["report_type"]
    report_label = context["report_label"]
    report_data = context["report_data"]
    is_subvencao = context.get("is_subvencao")
    is_emendas = context.get("is_emendas")

    story = []

    if report_type == "relatorio_final":
        valor_label = f"Valor autorizado por lei para o exercício de {_get_reference_year()}"
        story.extend(pdfmod.heading_with_body(
            Paragraph("1. Dados da Parceria", styles["h2"]),
            _partnership_data_table(report_data, is_subvencao, styles, valor_label=valor_label, anotacoes=report_data.get("anotacoes")),
        ))
        story.extend(pdfmod.heading_with_body(
            Paragraph("2. Objeto do Relatório", styles["h2"]), Paragraph(report_data.get("objeto_relatorio") or "Não informado.", styles["body"]),
        ))
        story.extend(pdfmod.heading_with_body(
            Paragraph("3. Referências", styles["h2"]), Paragraph(report_data.get("referencias") or "Não informado.", styles["body"]),
        ))
        item4_blocks = pdfmod.glue_headings([
            Paragraph("a) Dos objetivos:", styles["h3"]), Paragraph(report_data.get("objetivos") or "Não informado.", styles["body"]),
            Paragraph("b) Das metas estabelecidas:", styles["h3"]), Paragraph(report_data.get("metas") or "Não informado.", styles["body"]),
            Paragraph("c) Das atividades:", styles["h3"]), Paragraph(report_data.get("atividades") or "Não informado.", styles["body"]),
            Paragraph("d) Dos resultados:", styles["h3"]), Paragraph(report_data.get("resultados") or "Não informado.", styles["body"]),
            Paragraph("e) Da execução financeira:", styles["h3"]),
            Paragraph(report_data.get("execucao_financeira") or "Não informado.", styles["body"]),
        ], styles)
        story.extend(pdfmod.heading_with_body(
            Paragraph("4. Descrição dos Objetivos, Metas, Atividades Previstas, Resultados e Execução Financeira", styles["h2"]), item4_blocks[0],
        ))
        story.extend(item4_blocks[1:])
        story.extend(pdfmod.heading_with_body(
            Paragraph("5. Cumprimento do Objeto", styles["h2"]), Paragraph(report_data.get("cumprimento_objeto_final") or "Não informado.", styles["body"]),
        ))
        if is_subvencao:
            story.extend(pdfmod.heading_with_body(
                Paragraph("6. Conclusão", styles["h2"]), Paragraph(report_data.get("conclusao") or "Não informado.", styles["body"]),
            ))

        primeiras = _signature_pair(
            report_data, "signature_tecnico", "tecnico_nome", "Técnico de Monitoramento",
            "signature_financeiro", "financeiro_nome", "Técnico Financeiro de Monitoramento",
        )
        if primeiras:
            # pinned=False: essa NAO e a ultima assinatura do documento --
            # ainda vem a secao de Homologacao com a 2a rodada de assinaturas
            # depois, entao flui normal em vez de ancorar no rodape aqui.
            story.append(pdfmod.signature_block(primeiras, styles, pinned=False))

        story.extend(pdfmod.heading_with_body(
            Paragraph("Homologação da Comissão de Monitoramento e Avaliação", styles["h2"]),
            Paragraph(report_data.get("texto_homologacao") or "Não informado.", styles["body"]),
        ))
        comissao = _signature_pair(
            report_data, "signature_comissao_tecnico", "comissao_tecnico_nome", "Comissão de Monitoramento — Técnico",
            "signature_comissao_financeiro", "comissao_financeiro_nome", "Comissão de Monitoramento — Financeiro",
        )
        if comissao:
            story.append(pdfmod.signature_block(comissao, styles))

    elif report_type == "parecer_conclusivo":
        story.extend(pdfmod.heading_with_body(
            Paragraph("1. Dados da Parceria", styles["h2"]), _partnership_data_table(report_data, is_subvencao, styles),
        ))
        item2_blocks = pdfmod.glue_headings([
            Paragraph(report_data.get("fundamentacao") or "Não informado.", styles["body"]),
            Paragraph("a) Quanto ao cumprimento do objeto:", styles["h3"]), Paragraph(report_data.get("cumprimento_objeto") or "Não informado.", styles["body"]),
            Paragraph("b) Quanto aos benefícios e impactos da parceria:", styles["h3"]), Paragraph(report_data.get("beneficios_impactos") or "Não informado.", styles["body"]),
        ], styles)
        story.extend(pdfmod.heading_with_body(Paragraph("2. Fundamentação", styles["h2"]), item2_blocks[0]))
        story.extend(item2_blocks[1:])

        title3 = "3. Sustentabilidade e Continuidade das Ações que Foram Objeto da Parceria" if is_subvencao else "3. Conclusão"
        story.extend(pdfmod.heading_with_body(
            Paragraph(title3, styles["h2"]), Paragraph(report_data.get("conclusao") or "Não informado.", styles["body"]),
        ))
        if is_subvencao:
            story.extend(pdfmod.heading_with_body(
                Paragraph("4. Conclusão", styles["h2"]), Paragraph(report_data.get("conclusao_final") or "Não informado.", styles["body"]),
            ))

        signatures = _signature_pair(
            report_data, "signature_tecnico", "tecnico_nome", "Gestor da Parceria — Técnico",
            "signature_financeiro", "financeiro_nome", "Gestor da Parceria — Financeiro",
        )
        if signatures:
            story.append(pdfmod.signature_block(signatures, styles))

    else:  # parecer_tecnico
        story.extend(pdfmod.heading_with_body(
            Paragraph("1. Objeto do Relatório", styles["h2"]), Paragraph(report_data.get("objeto_relatorio") or "Não informado.", styles["body"]),
        ))

        item2_blocks = pdfmod.glue_headings([
            Paragraph("A) Dos Objetivos", styles["h3"]), Paragraph(report_data.get("item2_a_objetivos") or "Não informado.", styles["body"]),
            Paragraph("B) Das Metas Estabelecidas — Qualitativas", styles["h3"]), Paragraph(report_data.get("item2_b_metas") or "Não informado.", styles["body"]),
            Paragraph("Quantitativas", styles["h3"]), Paragraph(report_data.get("item2_b_metas_quant") or "Não informado.", styles["body"]),
            Paragraph("C) Das Atividades", styles["h3"]), Paragraph(report_data.get("item2_c_atividades") or "Não informado.", styles["body"]),
        ], styles)
        story.extend(pdfmod.heading_with_body(
            Paragraph("2. Descrição dos Objetivos, Metas, Atividades Previstas", styles["h2"]), item2_blocks[0],
        ))
        story.extend(item2_blocks[1:])

        story.extend(pdfmod.heading_with_body(
            Paragraph("3. Resultados", styles["h2"]), Paragraph(report_data.get("item3_resultados") or "Não informado.", styles["body"]),
        ))

        if report_data.get("item5_enabled"):
            pse_blocks = [Paragraph(f"Período: {report_data.get('item5_periodo') or 'Não informado'}", styles["body"])]
            qualitativos = [
                row for row in (report_data.get("item5_qualitativos") or [])
                if any(row.get(k) for k in ("data", "situacao", "recomendacoes", "observacao"))
            ]
            if qualitativos:
                pse_blocks.append(Paragraph("a) Qualitativos", styles["h3"]))
                pse_blocks.append(pdfmod.styled_table(
                    ["Data", "Situação Encontrada", "Recomendações", "Observação"],
                    [[row.get("data", "-"), row.get("situacao", "-"), row.get("recomendacoes", "-"), row.get("observacao", "-")] for row in qualitativos],
                    styles,
                ))
            pse_blocks.append(Paragraph("b) Quantitativos", styles["h3"]))
            pse_blocks.append(_quant_table(report_data.get("item5_quantitativos"), styles))
            pse_blocks = pdfmod.glue_headings(pse_blocks, styles)
            story.extend(pdfmod.heading_with_body(Paragraph("4. Dados", styles["h2"]), pse_blocks[0]))
            story.extend(pse_blocks[1:])

        narrativa = _cumprimento_narrativa(report_data, osc.name, is_subvencao, is_emendas)
        titulo5 = "5. Cumprimento do Objeto" + ("" if is_emendas else " até a Presente Data")
        story.extend(pdfmod.heading_with_body(Paragraph(titulo5, styles["h2"]), Paragraph(narrativa, styles["body"])))

        signatures = _signature_pair(
            report_data.get("assinaturas") or {}, "tecnico1", "tecnico1_nome", "Técnico Responsável",
            "tecnico2", "tecnico2_nome", "Técnico Responsável",
        )
        if signatures:
            story.append(pdfmod.signature_block(signatures, styles))

    filename = f"{report_type}-{osc.name}.pdf".replace(" ", "-")
    return pdfmod.pdf_response(report_label, f"{directorate.name} - {osc.name}", story, filename)

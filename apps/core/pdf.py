"""Geracao de PDF server-side (ReportLab) para os documentos do sistema.

Segue o mesmo espirito de apps/core/export.py (Excel): primitivas
reaproveitaveis + uma funcao por documento que monta a "historia" (lista de
flowables) e devolve um HttpResponse. Ver docs/dominio ou o plano da sessao
para o mapeamento completo dos 4 documentos que usam este modulo.
"""
import io
from datetime import datetime
from html.parser import HTMLParser
from urllib.request import urlopen

from django.contrib.staticfiles import finders
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

BRAND_BLUE = colors.HexColor("#1E3A8A")
BRAND_BLUE_SOFT = colors.HexColor("#EFF6FF")
TEXT_DARK = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#64748B")
BORDER_GRAY = colors.HexColor("#CBD5E1")

PAGE_SIZE = A4
SIDE_MARGIN = 18 * mm
TOP_MARGIN = 31 * mm
BOTTOM_MARGIN = 16 * mm
# Paginas 2+ nao desenham o cabecalho (logo/titulo) - so o rodape - entao
# ganham uma margem superior bem menor em vez de repetir os 31mm em branco.
LATER_PAGE_TOP_MARGIN = 16 * mm

INSTITUTION_LINE = "PREFEITURA DE UBERLANDIA - SECRETARIA MUNICIPAL DE DESENVOLVIMENTO SOCIAL"


def build_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("DocH1", parent=base["Heading1"], fontName="Helvetica-Bold",
                              fontSize=14, leading=17, textColor=BRAND_BLUE,
                              spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("DocH2", parent=base["Heading2"], fontName="Helvetica-Bold",
                              fontSize=11.5, leading=14, textColor=BRAND_BLUE,
                              spaceBefore=12, spaceAfter=5),
        "h3": ParagraphStyle("DocH3", parent=base["Heading3"], fontName="Helvetica-Bold",
                              fontSize=10.5, leading=13, textColor=TEXT_DARK,
                              spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("DocBody", parent=base["Normal"], fontName="Helvetica",
                                fontSize=9.5, leading=14, textColor=TEXT_DARK, spaceAfter=6),
        "body_empty": ParagraphStyle("DocBodyEmpty", parent=base["Normal"], fontName="Helvetica-Oblique",
                                      fontSize=9.5, leading=14, textColor=TEXT_MUTED, spaceAfter=6),
        "label": ParagraphStyle("DocLabel", parent=base["Normal"], fontName="Helvetica-Bold",
                                 fontSize=7.5, leading=10, textColor=TEXT_MUTED, spaceAfter=1),
        "value": ParagraphStyle("DocValue", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=9.5, leading=12, textColor=TEXT_DARK, spaceAfter=6),
        "cell": ParagraphStyle("DocCell", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.5, leading=11, textColor=TEXT_DARK),
        "cell_header": ParagraphStyle("DocCellHeader", parent=base["Normal"], fontName="Helvetica-Bold",
                                       fontSize=8.5, leading=11, textColor=colors.white),
        "list_item": ParagraphStyle("DocListItem", parent=base["Normal"], fontName="Helvetica",
                                     fontSize=9.5, leading=14, textColor=TEXT_DARK),
        "blockquote": ParagraphStyle("DocBlockquote", parent=base["Normal"], fontName="Helvetica-Oblique",
                                      fontSize=9.5, leading=14, textColor=TEXT_MUTED,
                                      leftIndent=10 * mm, spaceAfter=6),
        "sig_name": ParagraphStyle("SigName", parent=base["Normal"], fontName="Helvetica-Bold",
                                    fontSize=9, leading=12, alignment=TA_CENTER, spaceBefore=3),
        "sig_role": ParagraphStyle("SigRole", parent=base["Normal"], fontName="Helvetica",
                                    fontSize=7.5, leading=10, textColor=TEXT_MUTED, alignment=TA_CENTER),
        "caption": ParagraphStyle("Caption", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=7.5, leading=10, textColor=TEXT_MUTED, alignment=TA_CENTER),
    }


# ---------------------------------------------------------------------------
# Documento base: cabecalho/rodape repetidos em toda pagina
# ---------------------------------------------------------------------------

def _resolve_logo_reader():
    """Mesma logica de apps/core/context_processors.py: le o logo_url
    configuravel em SystemSetting (padrao /static/img/logo-navbar.png), nao o
    static/img/logo.png fixo que este modulo usava antes — assim a logo do
    PDF sempre bate com a da navbar. Aceita tanto um path estatico quanto uma
    URL externa. Resolvido uma vez por documento (nao por pagina)."""
    try:
        from apps.core.models import SystemSetting
        settings_map = {item.key: item.value for item in SystemSetting.objects.all()}
        logo_url = settings_map.get("logo_url", "/static/img/logo-navbar.png")
    except Exception:
        logo_url = "/static/img/logo-navbar.png"

    if not logo_url:
        return None
    try:
        if logo_url.startswith("http://") or logo_url.startswith("https://"):
            with urlopen(logo_url, timeout=8) as resp:
                data = resp.read()
            return ImageReader(io.BytesIO(data))
        static_path = logo_url
        if static_path.startswith("/static/"):
            static_path = static_path[len("/static/"):]
        elif static_path.startswith("static/"):
            static_path = static_path[len("static/"):]
        found = finders.find(static_path)
        return ImageReader(found) if found else None
    except Exception:
        return None


class SystemDocTemplate(BaseDocTemplate):
    """Cabecalho (logo/instituicao/titulo) so na 1a pagina - paginas seguintes
    repetiam o mesmo bloco antes (2026-08-17, pedido do usuario: em documentos
    de mais de 1 pagina, o cabecalho nao deve se repetir). Usa 2 PageTemplates
    ("first" com o cabecalho, "later" so com o rodape) + NextPageTemplate pra
    trocar a partir da 2a pagina - o padrao de "papel timbrado" do ReportLab.
    O rodape (numero de pagina/gerado em) continua em toda pagina, igual antes."""

    def __init__(self, buffer, doc_title, doc_subtitle, **kwargs):
        self.doc_title = doc_title
        self.doc_subtitle = doc_subtitle
        self._logo_reader = _resolve_logo_reader()
        kwargs.setdefault("pagesize", PAGE_SIZE)
        kwargs.setdefault("topMargin", TOP_MARGIN)
        kwargs.setdefault("bottomMargin", BOTTOM_MARGIN)
        kwargs.setdefault("leftMargin", SIDE_MARGIN)
        kwargs.setdefault("rightMargin", SIDE_MARGIN)
        super().__init__(buffer, **kwargs)
        frame_first = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="first")
        later_height = PAGE_SIZE[1] - LATER_PAGE_TOP_MARGIN - self.bottomMargin
        frame_later = Frame(self.leftMargin, self.bottomMargin, self.width, later_height, id="later")
        self.addPageTemplates([
            PageTemplate(id="first", frames=[frame_first], onPage=self._draw_chrome_first),
            PageTemplate(id="later", frames=[frame_later], onPage=self._draw_chrome_later),
        ])

    def _draw_header(self, canvas, doc):
        page_w, page_h = PAGE_SIZE
        text_x = self.leftMargin
        if self._logo_reader:
            try:
                canvas.drawImage(self._logo_reader, self.leftMargin, page_h - 25 * mm,
                                  width=13 * mm, height=13 * mm,
                                  preserveAspectRatio=True, mask="auto", anchor="nw")
                text_x = self.leftMargin + 16 * mm
            except Exception:
                pass
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(text_x, page_h - 10.5 * mm, INSTITUTION_LINE)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(BRAND_BLUE)
        canvas.drawString(text_x, page_h - 16 * mm, self.doc_title)
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(text_x, page_h - 20.5 * mm, self.doc_subtitle)
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.6)
        canvas.line(self.leftMargin, page_h - 26.5 * mm, page_w - self.rightMargin, page_h - 26.5 * mm)

    def _draw_footer(self, canvas, doc):
        page_w, page_h = PAGE_SIZE
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(self.leftMargin, 10 * mm,
                           "Gerado pelo Sistema de Vigilancia Socioassistencial em "
                           + datetime.now().strftime("%d/%m/%Y %H:%M"))
        canvas.drawRightString(page_w - self.rightMargin, 10 * mm, f"Pagina {doc.page}")

    def _draw_chrome_first(self, canvas, doc):
        canvas.saveState()
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)
        canvas.restoreState()

    def _draw_chrome_later(self, canvas, doc):
        canvas.saveState()
        self._draw_footer(canvas, doc)
        canvas.restoreState()


def pdf_response(doc_title, doc_subtitle, story, filename):
    buffer = io.BytesIO()
    doc = SystemDocTemplate(buffer, doc_title, doc_subtitle)
    # NextPageTemplate so faz efeito a partir da PROXIMA quebra de pagina -
    # a 1a pagina continua usando o template "first" (registrado primeiro),
    # com cabecalho; da 2a em diante usa "later" (so rodape).
    doc.build([NextPageTemplate("later")] + list(story))
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Helpers genericos de layout
# ---------------------------------------------------------------------------

def heading_with_body(heading_flowable, *body_flowables):
    """Gruda o titulo com o INICIO do conteudo (proximo flowable), deixando
    o resto fluir normalmente -- evita heading isolado no fim de uma pagina,
    separado do comeco do proprio conteudo. Sempre devolve uma LISTA de
    flowables (pra usar com story.extend(...) direto)."""
    if not body_flowables:
        return [KeepTogether([heading_flowable])]
    first = body_flowables[0]
    if isinstance(first, KeepTogether):
        # Nunca aninhar KeepTogether dentro de outro KeepTogether:
        # KeepTogether.wrap() sempre devolve uma altura gigante de proposito
        # (pra forcar split() a decidir), entao um KeepTogether aninhado
        # como item de outro faz o de fora "achar" que o grupo inteiro nao
        # cabe em lugar nenhum -- manda tudo pra proxima pagina mesmo
        # sobrando espaco de sobra na atual. Achata um nivel em vez disso.
        glued = [heading_flowable] + list(first._content)
    else:
        glued = [heading_flowable, first]
    rest = list(body_flowables[1:])
    return [KeepTogether(glued)] + rest


def label_value(label, value, styles):
    value = value if (value not in (None, "")) else "-"
    return [Paragraph(label, styles["label"]), Paragraph(str(value), styles["value"])]


def styled_table(headers, rows, styles, col_widths=None, header_bg=BRAND_BLUE):
    """Table com repeatRows=1: quando a tabela precisa quebrar entre paginas,
    o ReportLab automaticamente repete a linha de cabecalho na pagina
    seguinte e nunca deixa so o cabecalho (sem nenhuma linha de dado) sozinho
    numa pagina -- se nao cabe cabecalho + 1 linha, a tabela inteira desce."""
    header_row = [Paragraph(str(h), styles["cell_header"]) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([
            cell if isinstance(cell, Flowable) else Paragraph(str(cell) if cell not in (None, "") else "-", styles["cell"])
            for cell in row
        ])
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_BLUE_SOFT]),
    ]))
    return table


class PinnedToBottom(Flowable):
    """Ancora um flowable (ex.: bloco de assinaturas) rente a margem inferior
    de qualquer pagina em que ele acabar caindo. Estrategia: `wrap()` sempre
    reivindica a altura DISPONIVEL inteira do frame (assim o motor de layout
    do Platypus nunca tenta encaixar outro flowable embaixo dele na mesma
    pagina); `split()` empurra o conteudo inteiro pra proxima pagina quando
    ele nao cabe no espaco restante da pagina atual, ao inves de cortar/
    espremer -- na proxima pagina ele recebe a altura cheia e se ancora ai.
    """

    def __init__(self, inner):
        super().__init__()
        self.inner = inner
        self._inner_h = 0

    def _wrap_inner(self, availWidth, availHeight):
        # Flowables como KeepTogether precisam de `.canv` setado neles
        # mesmos pra medir (usam stringWidth do canvas ativo) -- o Frame so
        # seta isso no flowable de topo (este PinnedToBottom), entao
        # propagamos manualmente pro conteudo interno antes de wrap()/split().
        if hasattr(self, "canv"):
            self.inner.canv = self.canv
        return self.inner.wrap(availWidth, availHeight)

    def wrap(self, availWidth, availHeight):
        inner_h = self._wrap_inner(availWidth, availHeight)[1]
        self._inner_h = inner_h
        if inner_h <= availHeight:
            # Cabe no espaco restante desta pagina: reivindica a altura
            # DISPONIVEL inteira (nao so a do conteudo) -- assim o Frame nao
            # tenta encaixar mais nada abaixo, e o conteudo real e desenhado
            # colado no fundo dessa area em draw().
            self._claim_h = availHeight
        else:
            # Nao cabe nem sozinho no espaco restante: reivindica MAIS do
            # que availHeight de proposito, pra forcar o Frame a chamar
            # split() em vez de desenhar aqui.
            self._claim_h = availHeight + inner_h
        return (availWidth, self._claim_h)

    def split(self, availWidth, availHeight):
        inner_h = self._wrap_inner(availWidth, availHeight)[1]
        if inner_h <= availHeight:
            # Devolver [self]: o Frame tenta de novo (agora numa pagina/
            # frame nova, com availHeight cheio) e dessa vez wrap() cai no
            # ramo "cabe" acima.
            return [self]
        # Nem numa pagina nova inteira caberia com o availHeight visto aqui
        # (nao deveria acontecer em uso normal) -- desiste de encaixar,
        # Platypus tenta de novo do zero na proxima frame.
        return []

    def draw(self):
        self.inner.drawOn(self.canv, 0, 0)


# ---------------------------------------------------------------------------
# HTML rico (Quill/nh3) -> flowables
# ---------------------------------------------------------------------------

_INLINE_TAG_MAP = {
    "strong": "b", "b": "b",
    "em": "i", "i": "i",
    "u": "u",
    "s": "strike", "strike": "strike",
    "a": "a",
    "br": "br",
}


class _Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ("br",):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_markup(node):
    """Serializa um _Node (ou string) recursivamente pro mini-markup que
    Paragraph do ReportLab entende nativamente (<b>,<i>,<u>,<strike>,<a>,<br/>)."""
    if isinstance(node, str):
        return _escape(node)
    tag = _INLINE_TAG_MAP.get(node.tag)
    inner = "".join(_inline_markup(child) for child in node.children)
    if tag == "br":
        return "<br/>"
    if tag == "a":
        href = _escape(node.attrs.get("href", ""))
        return f'<a href="{href}" color="#1E3A8A">{inner}</a>' if href else inner
    if tag:
        return f"<{tag}>{inner}</{tag}>"
    return inner


def _block_text(node):
    text = _inline_markup(node).strip()
    return text


def _is_heading_like_paragraph(node):
    """<p> cujo unico conteudo e um <strong>/<b> curto -- convencao comum
    usada no editor Quill pra "titulo de secao" sem usar tag de heading de
    verdade."""
    real_children = [c for c in node.children if not (isinstance(c, str) and not c.strip())]
    if len(real_children) != 1:
        return False
    child = real_children[0]
    if not (isinstance(child, _Node) and child.tag in ("strong", "b")):
        return False
    text = _block_text(child)
    return bool(text) and len(text) <= 90


def html_to_flowables(html, styles):
    if not html or not html.strip():
        return [Paragraph("Nenhum conteudo informado.", styles["body_empty"])]

    builder = _TreeBuilder()
    builder.feed(html)
    flowables = []

    def walk_table(table_node):
        rows = []
        had_thead = False
        for child in table_node.children:
            if not isinstance(child, _Node):
                continue
            if child.tag in ("thead", "tbody"):
                if child.tag == "thead":
                    had_thead = True
                for tr in child.children:
                    if isinstance(tr, _Node) and tr.tag == "tr":
                        rows.append(tr)
            elif child.tag == "tr":
                rows.append(child)
        if not rows:
            return None
        data = []
        for tr in rows:
            cells = [c for c in tr.children if isinstance(c, _Node) and c.tag in ("td", "th")]
            data.append([Paragraph(_block_text(c) or "-", styles["cell_header"] if c.tag == "th" else styles["cell"]) for c in cells])
        if not data:
            return None
        first_row_is_header = had_thead or all(c.tag == "th" for c in
                                                 [c for c in rows[0].children if isinstance(c, _Node) and c.tag in ("td", "th")])
        table = Table(data, repeatRows=1 if first_row_is_header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if first_row_is_header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE))
        table.setStyle(TableStyle(style))
        return table

    def walk_list(list_node, ordered):
        items = []
        for child in list_node.children:
            if isinstance(child, _Node) and child.tag == "li":
                items.append(ListItem(Paragraph(_block_text(child) or "-", styles["list_item"]), leftIndent=12))
        if not items:
            return None
        if ordered:
            return ListFlowable(items, bulletType="1", start="1", leftIndent=14)
        return ListFlowable(items, bulletType="bullet", leftIndent=14)

    for node in builder.root.children:
        if not isinstance(node, _Node):
            continue
        if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = _block_text(node)
            if text:
                heading_style = styles["h2"] if node.tag in ("h1", "h2") else styles["h3"]
                flowables.append(Paragraph(text, heading_style))
        elif node.tag == "p":
            text = _block_text(node)
            if not text:
                flowables.append(Spacer(1, 4))
            else:
                para = Paragraph(text, styles["body"])
                if _is_heading_like_paragraph(node):
                    # Conteudo real (Quill) raramente usa tags <h1-h6> de
                    # verdade -- "titulos" de secao normalmente sao so um
                    # paragrafo 100% em negrito. Marca pra glue_headings()
                    # tratar como heading tambem, sem mudar o estilo visual
                    # (mantem como o usuario formatou).
                    para._heading_like = True
                flowables.append(para)
        elif node.tag == "blockquote":
            text = _block_text(node)
            if text:
                flowables.append(Paragraph(text, styles["blockquote"]))
        elif node.tag in ("ul", "ol"):
            lst = walk_list(node, ordered=(node.tag == "ol"))
            if lst:
                flowables.append(lst)
        elif node.tag == "table":
            tbl = walk_table(node)
            if tbl:
                flowables.append(tbl)
        elif node.tag == "br":
            flowables.append(Spacer(1, 6))

    if not flowables:
        flowables.append(Paragraph("Nenhum conteudo informado.", styles["body_empty"]))
    return glue_headings(flowables, styles)


_HEADING_STYLE_NAMES = {"DocH1", "DocH2", "DocH3"}


def _is_heading_flowable(f):
    return isinstance(f, Paragraph) and (
        getattr(f.style, "name", None) in _HEADING_STYLE_NAMES or getattr(f, "_heading_like", False)
    )


def glue_headings(flowables, styles):
    """Pos-processa uma lista flat de flowables: toda sequencia de um ou
    mais "titulos" (heading de verdade OU paragrafo soh-negrito curto --
    ver _is_heading_like_paragraph) seguida de espacos em branco vira um
    unico bloco (KeepTogether) junto com o INICIO do conteudo real que vem
    depois -- pra nenhum titulo terminar uma pagina sozinho, separado do
    comeco do proprio conteudo."""
    glued = []
    i = 0
    n = len(flowables)
    while i < n:
        f = flowables[i]
        if not _is_heading_flowable(f):
            glued.append(f)
            i += 1
            continue
        run = [f]
        j = i + 1
        while j < n and (_is_heading_flowable(flowables[j]) or isinstance(flowables[j], Spacer)):
            run.append(flowables[j])
            j += 1
        if j < n:
            run.append(flowables[j])
            j += 1
        glued.append(KeepTogether(run) if len(run) > 1 else run[0])
        i = j
    return glued


# ---------------------------------------------------------------------------
# Assinaturas e fotos
# ---------------------------------------------------------------------------

def _decode_data_url_image(data_url, max_w=45 * mm, max_h=22 * mm):
    if not data_url or "," not in data_url or len(data_url) < 100:
        return None
    try:
        header, b64data = data_url.split(",", 1)
        import base64
        raw = base64.b64decode(b64data)
        # Decodifica os pixels de verdade aqui, nao so o header -- uma
        # imagem truncada/corrompida (ex.: assinatura salva pela metade)
        # passa despercebida por ImageReader.getSize() sozinho, e so estoura
        # MAIS TARDE dentro de doc.build() (fora de qualquer try/except),
        # derrubando o PDF inteiro com 500 em vez de so pular essa imagem.
        # Achado investigando "impressao do Relatorio Final bugada" (2026-08-16).
        from PIL import Image as PILImage
        pil_img = PILImage.open(io.BytesIO(raw))
        pil_img.load()
        reader = ImageReader(io.BytesIO(raw))
        iw, ih = reader.getSize()
        scale = min(max_w / iw, max_h / ih)
        return Image(io.BytesIO(raw), width=iw * scale, height=ih * scale)
    except Exception:
        return None


def signature_block(signatures, styles, pinned=True):
    """signatures: lista de {label, name, image} (image = data URL base64 ou None).
    Por padrao devolve um flowable ancorado no rodape da pagina em que cair
    (PinnedToBottom) -- use pinned=False para um bloco de assinaturas que
    flui normalmente no meio do documento (quando NAO e o ultimo elemento
    da pagina, ex.: relatorio_final tem duas rodadas de assinatura, so a
    segunda e a ultima coisa do documento)."""
    cols = []
    for sig in signatures:
        img = _decode_data_url_image(sig.get("image"))
        cell = []
        if img:
            cell.append(img)
        else:
            cell.append(Spacer(1, 16 * mm))
        cell.append(Paragraph("_" * 34, styles["sig_role"]))
        # Nome sempre em maiusculas -- reforcado aqui pra cobrir tambem
        # assinaturas salvas antes desse ajuste (2026-08-16).
        cell.append(Paragraph((sig.get("name") or "Nao assinado").upper(), styles["sig_name"]))
        cell.append(Paragraph(sig.get("label", ""), styles["sig_role"]))
        cols.append(cell)

    if not cols:
        return Spacer(1, 1)

    col_w = (PAGE_SIZE[0] - 2 * SIDE_MARGIN) / len(cols)
    table = Table([cols], colWidths=[col_w] * len(cols))
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    if not pinned:
        return table
    # Nao envolver em KeepTogether: KeepTogether.wrap() sempre reporta uma
    # altura gigante de proposito (forca split() a decidir) em vez da altura
    # real do conteudo -- quebraria a medicao que PinnedToBottom precisa
    # fazer. A Table sozinha ja funciona como unidade atomica aqui, porque
    # PinnedToBottom nunca chama split() no seu conteudo interno (so mede
    # com wrap() e desenha tudo de uma vez com drawOn()).
    return PinnedToBottom(table)


def _load_image_reader(url):
    try:
        if url.startswith("http://") or url.startswith("https://"):
            with urlopen(url, timeout=8) as resp:
                data = resp.read()
            return io.BytesIO(data)
        from django.conf import settings
        import os
        path = url
        if path.startswith("/media/"):
            path = path[len("/media/"):]
        full_path = os.path.join(str(settings.MEDIA_ROOT), path)
        if os.path.exists(full_path):
            with open(full_path, "rb") as fh:
                return io.BytesIO(fh.read())
    except Exception:
        return None
    return None


def photo_grid(documents, styles, columns=2):
    """documents: lista de {name, type, url}. So inclui itens com URL valida;
    falhas de download individuais sao ignoradas (nao derrubam o PDF)."""
    cell_w = (PAGE_SIZE[0] - 2 * SIDE_MARGIN) / columns - 4
    cells = []
    for doc in documents:
        url = doc.get("url")
        if not url:
            continue
        buf = _load_image_reader(url)
        if not buf:
            continue
        try:
            reader = ImageReader(buf)
            iw, ih = reader.getSize()
            scale = cell_w / iw
            img = Image(buf, width=cell_w, height=ih * scale)
        except Exception:
            continue
        caption = Paragraph(doc.get("name") or doc.get("type") or "", styles["caption"])
        cells.append(KeepTogether([img, caption]))

    if not cells:
        return Paragraph("Nenhuma foto/evidencia anexada.", styles["body_empty"])

    rows = [cells[i:i + columns] for i in range(0, len(cells), columns)]
    for row in rows:
        while len(row) < columns:
            row.append("")
    table = Table(rows, colWidths=[cell_w + 4] * columns)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


# ---------------------------------------------------------------------------
# Documento 1: Relatorio Mensal Narrativo (compartilhado por 9 apps, via
# NarrativeReportMixin.get() em apps/core/mixins.py)
# ---------------------------------------------------------------------------

def render_narrative_report_pdf(context):
    from apps.core.utils import MONTH_OPTIONS

    styles = build_styles()
    directorate = context["directorate"]
    month = context["selected_month"]
    year = context["selected_year"]
    report = context.get("monthly_report")
    report_label = context.get("report_label") or "Relatorio Mensal"
    month_label = dict(MONTH_OPTIONS).get(int(month), month)

    doc_title = "Relatorio Mensal Narrativo"
    doc_subtitle = f"{directorate.name} - {report_label} - {month_label}/{year}"

    story = [Paragraph(f"{month_label} de {year}", styles["h1"])]
    if report:
        status_label = {"draft": "Rascunho", "finalized": "Finalizado", "submitted": "Enviado"}.get(report.status, report.status)
        story.append(Paragraph(f"Status: {status_label}", styles["body"]))
    story.append(Spacer(1, 6))
    story.extend(html_to_flowables(context.get("report_content_html", ""), styles))

    filename = f"relatorio-narrativo-{directorate.name}-{month}-{year}.pdf".replace(" ", "-")
    return pdf_response(doc_title, doc_subtitle, story, filename)

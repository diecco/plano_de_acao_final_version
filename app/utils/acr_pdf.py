from datetime import datetime
from html import escape
from io import BytesIO
import os


LARANJA = "#F36B21"
CINZA_ESCURO = "#4B5055"
CINZA = "#6C757D"
CINZA_CLARO = "#F2F3F4"
BRANCO = "#FFFFFF"

ROTULOS_ETAPA = {
    "identificacao": "Identificação",
    "investigacao": "Investigação",
    "5_porques": "Investigação - 5 Porquês",
    "causas": "Causas",
    "acoes": "Ações",
    "eficacia": "Eficácia",
}


def _texto(valor, padrao="-"):
    if valor is None or valor == "":
        return padrao
    return str(valor)


def _data(valor, incluir_hora=False):
    if not valor:
        return "-"
    formato = "%d/%m/%Y %H:%M" if incluir_hora else "%d/%m/%Y"
    if hasattr(valor, "strftime"):
        return valor.strftime(formato)
    return str(valor)


def _paragrafo(valor, estilo, padrao="-"):
    from reportlab.platypus import Paragraph

    conteudo = escape(_texto(valor, padrao)).replace("\n", "<br/>")
    return Paragraph(conteudo, estilo)


def gerar_pdf_acr(dados, logo_path=None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate,
        CondPageBreak,
        Flowable,
        Frame,
        HRFlowable,
        Image,
        NextPageTemplate,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    margem_direita = 1.6 * cm
    margem_esquerda = 1.6 * cm
    margem_superior = 1.5 * cm
    margem_inferior = 1.6 * cm
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margem_direita,
        leftMargin=margem_esquerda,
        topMargin=margem_superior,
        bottomMargin=margem_inferior,
        title=f"Relatório ACR {dados['investigacao'].get('numero', '')}",
        author="TrackPlan",
        subject="Análise de Causa Raiz",
    )

    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "TituloACR",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloACR",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor(CINZA),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "secao": ParagraphStyle(
            "SecaoACR",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(LARANJA),
            spaceBefore=9,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "NormalACR",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_LEFT,
        ),
        "pequeno": ParagraphStyle(
            "PequenoACR",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor(CINZA_ESCURO),
        ),
        "rotulo": ParagraphStyle(
            "RotuloACR",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor(CINZA),
        ),
        "cabecalho": ParagraphStyle(
            "CabecalhoTabelaACR",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.3,
            leading=9,
            textColor=colors.HexColor(BRANCO),
        ),
    }

    def tabela(dados_tabela, larguras, cabecalho=True, fonte=7.5):
        resultado = Table(
            dados_tabela,
            colWidths=larguras,
            repeatRows=1 if cabecalho else 0,
            hAlign="LEFT",
        )
        comandos = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), fonte),
        ]
        if cabecalho:
            comandos.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LARANJA)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        for linha in range(1 if cabecalho else 0, len(dados_tabela)):
            if linha % 2 == 0:
                comandos.append(
                    ("BACKGROUND", (0, linha), (-1, linha), colors.HexColor("#FAFAFA"))
                )
        resultado.setStyle(TableStyle(comandos))
        return resultado

    def titulo_secao(numero, titulo):
        return Paragraph(f"{numero}. {escape(titulo)}", estilos["secao"])

    def decorar_pagina(canvas, documento):
        canvas.saveState()
        largura, _ = canvas._pagesize
        canvas.setStrokeColor(colors.HexColor(LARANJA))
        canvas.setLineWidth(1.2)
        canvas.line(doc.leftMargin, 1.15 * cm, largura - doc.rightMargin, 1.15 * cm)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            doc.leftMargin,
            0.72 * cm,
            f"TrackPlan - Análise de Causa Raiz | Gerado em {gerado_em}",
        )
        canvas.drawRightString(
            largura - doc.rightMargin,
            0.72 * cm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    retrato = Frame(
        margem_esquerda,
        margem_inferior,
        A4[0] - margem_esquerda - margem_direita,
        A4[1] - margem_superior - margem_inferior,
        id="retrato_frame",
    )
    pagina_paisagem = landscape(A4)
    paisagem = Frame(
        margem_esquerda,
        margem_inferior,
        pagina_paisagem[0] - margem_esquerda - margem_direita,
        pagina_paisagem[1] - margem_superior - margem_inferior,
        id="paisagem_frame",
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="retrato", pagesize=A4, frames=[retrato], onPage=decorar_pagina),
            PageTemplate(
                id="paisagem",
                pagesize=pagina_paisagem,
                frames=[paisagem],
                onPage=decorar_pagina,
            ),
        ]
    )

    class ArvoreCausasFlowable(Flowable):
        """Prancha vetorial da árvore, dimensionada para uma página."""

        def __init__(self, evento, itens, classificacoes, largura, altura):
            super().__init__()
            self.evento = _texto(evento, "Evento indesejado")
            self.itens = itens
            self.classificacoes = classificacoes
            self.width = largura
            self.height = altura

        @staticmethod
        def _linhas(texto, largura, canvas, fonte, tamanho, limite=3):
            linhas, atual = [], ""
            for palavra in _texto(texto).split():
                candidata = f"{atual} {palavra}".strip()
                if not atual or canvas.stringWidth(candidata, fonte, tamanho) <= largura:
                    atual = candidata
                else:
                    linhas.append(atual)
                    atual = palavra
            if atual:
                linhas.append(atual)
            if len(linhas) > limite:
                linhas = linhas[:limite]
                ultima = linhas[-1]
                while ultima and canvas.stringWidth(ultima + "...", fonte, tamanho) > largura:
                    ultima = ultima[:-1]
                linhas[-1] = ultima.rstrip() + "..."
            return linhas

        def draw(self):
            canvas = self.canv
            card_w, card_h = 156.0, 56.0
            gap_x, gap_y, evento_h = 20.0, 62.0, 58.0
            por_pai, por_id = {}, {}
            for indice, item in enumerate(self.itens):
                item_id = item.get("id") or f"item-{indice}"
                por_id[item_id] = item
                por_pai.setdefault(item.get("parent_id"), []).append(item_id)
            for pai_id in por_pai:
                por_pai[pai_id].sort(
                    key=lambda item_id: (por_id[item_id].get("ordem") or 0, str(item_id))
                )

            raizes = por_pai.get(None, [])
            larguras, visitando = {}, set()

            def largura_subarvore(item_id):
                if item_id in larguras:
                    return larguras[item_id]
                if item_id in visitando:
                    return card_w
                visitando.add(item_id)
                filhos = por_pai.get(item_id, [])
                largura = card_w
                if filhos:
                    largura = max(
                        card_w,
                        sum(largura_subarvore(filho) for filho in filhos)
                        + gap_x * (len(filhos) - 1),
                    )
                visitando.discard(item_id)
                larguras[item_id] = largura
                return largura

            largura_arvore = (
                sum(largura_subarvore(item_id) for item_id in raizes)
                + gap_x * max(0, len(raizes) - 1)
            ) or card_w
            posicoes, profundidade_maxima = {}, 0

            def posicionar(item_id, esquerda, nivel):
                nonlocal profundidade_maxima
                profundidade_maxima = max(profundidade_maxima, nivel)
                largura = larguras[item_id]
                posicoes[item_id] = (esquerda + largura / 2, nivel)
                cursor = esquerda
                for filho in por_pai.get(item_id, []):
                    posicionar(filho, cursor, nivel + 1)
                    cursor += larguras[filho] + gap_x

            cursor = 0.0
            for item_id in raizes:
                posicionar(item_id, cursor, 1)
                cursor += larguras[item_id] + gap_x

            altura_arvore = evento_h + 42 + profundidade_maxima * (card_h + gap_y)
            escala = min(
                1.0,
                (self.width - 12) / largura_arvore,
                (self.height - 12) / max(altura_arvore, 1),
            )
            offset_x = (self.width - largura_arvore * escala) / 2
            canvas.saveState()
            canvas.translate(offset_x, self.height - 6)
            canvas.scale(escala, escala)

            evento_w = min(max(card_w * 1.8, 300), largura_arvore)
            evento_x, evento_y = largura_arvore / 2, -evento_h
            canvas.setFillColor(colors.HexColor(LARANJA))
            canvas.setStrokeColor(colors.HexColor(LARANJA))
            canvas.roundRect(
                evento_x - evento_w / 2, evento_y, evento_w, evento_h, 10, fill=1, stroke=1
            )
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawCentredString(evento_x, evento_y + evento_h - 15, "EVENTO INDESEJADO")
            canvas.setFont("Helvetica-Bold", 10)
            for indice, linha in enumerate(
                self._linhas(self.evento, evento_w - 24, canvas, "Helvetica-Bold", 10, 2)
            ):
                canvas.drawCentredString(evento_x, evento_y + evento_h - 32 - indice * 12, linha)

            def coordenadas(item_id):
                centro_x, nivel = posicoes[item_id]
                topo_y = -evento_h - 42 - (nivel - 1) * (card_h + gap_y)
                return centro_x, topo_y

            canvas.setStrokeColor(colors.HexColor(CINZA))
            canvas.setLineWidth(1.15)
            for item_id, item in por_id.items():
                if item_id not in posicoes:
                    continue
                filho_x, filho_topo = coordenadas(item_id)
                pai_id = item.get("parent_id")
                if pai_id in posicoes:
                    pai_x, pai_topo = coordenadas(pai_id)
                    pai_base = pai_topo - card_h
                else:
                    pai_x, pai_base = evento_x, evento_y
                meio_y = (filho_topo + pai_base) / 2
                canvas.line(filho_x, filho_topo, filho_x, meio_y)
                canvas.line(filho_x, meio_y, pai_x, meio_y)
                canvas.line(pai_x, meio_y, pai_x, pai_base)
                canvas.setFillColor(colors.HexColor(CINZA))
                seta = canvas.beginPath()
                seta.moveTo(pai_x, pai_base)
                seta.lineTo(pai_x - 3.4, pai_base - 5.5)
                seta.lineTo(pai_x + 3.4, pai_base - 5.5)
                seta.close()
                canvas.drawPath(seta, fill=1, stroke=0)

            for item_id, item in por_id.items():
                if item_id not in posicoes:
                    continue
                centro_x, topo_y = coordenadas(item_id)
                esquerda, base_y = centro_x - card_w / 2, topo_y - card_h
                canvas.setFillColor(colors.white)
                canvas.setStrokeColor(colors.HexColor("#D8DADD"))
                canvas.roundRect(esquerda, base_y, card_w, card_h, 7, fill=1, stroke=1)
                canvas.setStrokeColor(colors.HexColor(LARANJA))
                canvas.setLineWidth(2.2)
                canvas.line(esquerda, base_y + 7, esquerda, topo_y - 7)
                classificacao = self.classificacoes.get(
                    item.get("classificacao"), item.get("classificacao") or "Potencial"
                )
                canvas.setFillColor(colors.HexColor(LARANJA))
                canvas.setFont("Helvetica-Bold", 7.3)
                canvas.drawString(esquerda + 9, topo_y - 14, _texto(classificacao).upper())
                canvas.setFillColor(colors.HexColor(CINZA_ESCURO))
                canvas.setFont("Helvetica", 8.2)
                for indice, linha in enumerate(
                    self._linhas(item.get("descricao"), card_w - 18, canvas, "Helvetica", 8.2)
                ):
                    canvas.drawString(esquerda + 9, topo_y - 29 - indice * 10, linha)

            if not raizes:
                canvas.setFillColor(colors.HexColor(CINZA))
                canvas.setFont("Helvetica", 10)
                canvas.drawCentredString(
                    largura_arvore / 2, evento_y - 35, "Nenhum fato antecedente registrado."
                )
            canvas.restoreState()

    investigacao = dados["investigacao"]
    elementos = []
    if logo_path and os.path.isfile(logo_path):
        logo = Image(logo_path, width=3.1 * cm, height=1.25 * cm, kind="proportional")
        logo.hAlign = "CENTER"
        elementos.extend([logo, Spacer(1, 0.15 * cm)])
    elementos.append(Paragraph("ANÁLISE DE CAUSA RAIZ", estilos["titulo"]))
    elementos.append(
        Paragraph(
            f"{escape(_texto(investigacao.get('numero')))} - "
            f"{escape(_texto(investigacao.get('metodologia')))}",
            estilos["subtitulo"],
        )
    )
    elementos.append(HRFlowable(width="100%", color=colors.HexColor(LARANJA), thickness=1.2))
    elementos.append(Spacer(1, 0.2 * cm))

    elementos.append(titulo_secao(1, "Identificação e contexto"))
    contexto = [
        [
            _paragrafo("Número", estilos["rotulo"]),
            _paragrafo(investigacao.get("numero"), estilos["normal"]),
            _paragrafo("Status", estilos["rotulo"]),
            _paragrafo(investigacao.get("status"), estilos["normal"]),
        ],
        [
            _paragrafo("Origem", estilos["rotulo"]),
            _paragrafo(investigacao.get("origem"), estilos["normal"]),
            _paragrafo("Classificação", estilos["rotulo"]),
            _paragrafo(investigacao.get("classificacao"), estilos["normal"]),
        ],
        [
            _paragrafo("Gravidade", estilos["rotulo"]),
            _paragrafo(investigacao.get("gravidade"), estilos["normal"]),
            _paragrafo("Centro de custos", estilos["rotulo"]),
            _paragrafo(
                f"{_texto(investigacao.get('centro_codigo'))} - "
                f"{_texto(investigacao.get('centro_descricao'))}",
                estilos["normal"],
            ),
        ],
        [
            _paragrafo("Responsável", estilos["rotulo"]),
            _paragrafo(investigacao.get("responsavel"), estilos["normal"]),
            _paragrafo("Criador", estilos["rotulo"]),
            _paragrafo(investigacao.get("criador"), estilos["normal"]),
        ],
        [
            _paragrafo("Data da ocorrência", estilos["rotulo"]),
            _paragrafo(_data(investigacao.get("data_ocorrencia")), estilos["normal"]),
            _paragrafo("Data da investigação", estilos["rotulo"]),
            _paragrafo(_data(investigacao.get("data_investigacao")), estilos["normal"]),
        ],
        [
            _paragrafo("Equipamento / processo", estilos["rotulo"]),
            _paragrafo(investigacao.get("equipamento_processo"), estilos["normal"]),
            _paragrafo("Participantes", estilos["rotulo"]),
            _paragrafo(", ".join(dados.get("participantes", [])), estilos["normal"]),
        ],
    ]
    contexto_tabela = Table(contexto, colWidths=[2.6 * cm, 5.9 * cm, 2.6 * cm, 5.9 * cm])
    contexto_tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(CINZA_CLARO)),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(CINZA_CLARO)),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elementos.append(contexto_tabela)
    elementos.append(Spacer(1, 0.2 * cm))
    elementos.append(_paragrafo("Descrição da ocorrência", estilos["rotulo"] ))
    elementos.append(_paragrafo(investigacao.get("descricao_ocorrencia"), estilos["normal"]))

    metodologia_6m = investigacao.get("metodologia_codigo") == "ishikawa"
    metodologia_arvore = (
        investigacao.get("metodologia_codigo") == "arvore_causas"
    )
    titulo_metodologia = "Investigação - 5 Porquês"
    if metodologia_6m:
        titulo_metodologia = "Investigação - 6M (Ishikawa)"
    elif metodologia_arvore:
        titulo_metodologia = "Investigação - Árvore de Causas"
    if metodologia_arvore:
        elementos.extend([NextPageTemplate("paisagem"), PageBreak()])
        elementos.append(titulo_secao(2, titulo_metodologia))
        elementos.append(
            _paragrafo(
                "Os conectores indicam a relação entre os fatos antecedentes e o evento indesejado.",
                estilos["pequeno"],
            )
        )
        elementos.append(Spacer(1, 0.2 * cm))
        elementos.append(
            ArvoreCausasFlowable(
                investigacao.get("descricao_ocorrencia"),
                dados.get("itens_arvore_causas", []),
                dados.get("classificacoes_arvore_causas", {}),
                pagina_paisagem[0] - margem_esquerda - margem_direita - 12,
                15.6 * cm,
            )
        )
        elementos.extend([NextPageTemplate("retrato"), PageBreak()])
    else:
        elementos.append(titulo_secao(2, titulo_metodologia))
    if metodologia_6m:
        categorias = dados.get("categorias_6m", {})
        classificacoes = dados.get("classificacoes_6m", {})
        porques = [
            {
                "ordem": categorias.get(item.get("categoria"), "6M"),
                "pergunta": classificacoes.get(
                    item.get("classificacao"),
                    item.get("classificacao") or "Potencial",
                ),
                "resposta": item.get("descricao"),
            }
            for item in dados.get("itens_6m", [])
        ]
    elif metodologia_arvore:
        porques = []
    else:
        porques = dados.get("porques", [])
    if metodologia_arvore:
        pass
    elif porques:
        linhas = [[
            Paragraph("Categoria" if metodologia_6m else "Nível", estilos["cabecalho"]),
            Paragraph(
                "Classificação"
                if metodologia_6m or metodologia_arvore
                else "Pergunta",
                estilos["cabecalho"],
            ),
            Paragraph(
                "Fato antecedente"
                if metodologia_arvore
                else ("Hipótese" if metodologia_6m else "Resposta"),
                estilos["cabecalho"],
            ),
        ]]
        for item in porques:
            linhas.append(
                [
                    _paragrafo(
                        item.get("ordem") if metodologia_6m or metodologia_arvore
                        else f"{item.get('ordem')}o",
                        estilos["pequeno"],
                    ),
                    _paragrafo(item.get("pergunta"), estilos["pequeno"]),
                    _paragrafo(item.get("resposta"), estilos["pequeno"]),
                ]
            )
        larguras_investigacao = (
            [3.5 * cm, 3.5 * cm, 10 * cm]
            if metodologia_6m or metodologia_arvore
            else [1.2 * cm, 7.9 * cm, 7.9 * cm]
        )
        elementos.append(tabela(linhas, larguras_investigacao))
    else:
        elementos.append(_paragrafo("Etapa ainda não preenchida.", estilos["normal"]))

    elementos.append(titulo_secao(3, "Causa raiz"))
    causas = dados.get("causas_raiz") or (
        [dados.get("causa_raiz")] if dados.get("causa_raiz") else []
    )
    if causas:
        bloco_causa = Table(
            [
                [_paragrafo(causa.get("descricao"), estilos["normal"])]
                for causa in causas
            ],
            colWidths=[17 * cm],
        )
        bloco_causa.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(LARANJA)),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4ED")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elementos.append(bloco_causa)
    else:
        elementos.append(_paragrafo("Causa raiz ainda não confirmada.", estilos["normal"]))

    elementos.append(titulo_secao(4, "Plano de ação"))
    acoes = dados.get("acoes", [])
    if acoes:
        linhas = [[
            Paragraph("Ação", estilos["cabecalho"]),
            Paragraph("Responsável", estilos["cabecalho"]),
            Paragraph("Prazo", estilos["cabecalho"]),
            Paragraph("Conclusão", estilos["cabecalho"]),
            Paragraph("Status", estilos["cabecalho"]),
        ]]
        for acao in acoes:
            descricao = acao.get("descricao") or "-"
            if acao.get("observacoes"):
                descricao += f"\nObservações: {acao['observacoes']}"
            linhas.append(
                [
                    _paragrafo(descricao, estilos["pequeno"]),
                    _paragrafo(acao.get("responsavel"), estilos["pequeno"]),
                    _paragrafo(_data(acao.get("prazo")), estilos["pequeno"]),
                    _paragrafo(_data(acao.get("data_conclusao")), estilos["pequeno"]),
                    _paragrafo(acao.get("status"), estilos["pequeno"]),
                ]
            )
        elementos.append(
            tabela(
                linhas,
                [7.1 * cm, 3.3 * cm, 2.1 * cm, 2.1 * cm, 2.4 * cm],
                fonte=7,
            )
        )
    else:
        elementos.append(_paragrafo("Nenhuma acao vinculada.", estilos["normal"]))

    elementos.append(titulo_secao(5, "Verificação de eficácia"))
    verificacoes = dados.get("verificacoes", [])
    if verificacoes:
        linhas = [[
            Paragraph("Ciclo", estilos["cabecalho"]),
            Paragraph("Prevista", estilos["cabecalho"]),
            Paragraph("Realizada", estilos["cabecalho"]),
            Paragraph("Critério", estilos["cabecalho"]),
            Paragraph("Resultado", estilos["cabecalho"]),
        ]]
        for verificacao in verificacoes:
            criterio = verificacao.get("criterio") or "-"
            if verificacao.get("justificativa"):
                criterio += f"\nJustificativa: {verificacao['justificativa']}"
            linhas.append(
                [
                    _paragrafo(verificacao.get("ciclo"), estilos["pequeno"]),
                    _paragrafo(_data(verificacao.get("data_prevista")), estilos["pequeno"]),
                    _paragrafo(_data(verificacao.get("data_realizada")), estilos["pequeno"]),
                    _paragrafo(criterio, estilos["pequeno"]),
                    _paragrafo(verificacao.get("resultado") or "Pendente", estilos["pequeno"]),
                ]
            )
        elementos.append(tabela(linhas, [1.2 * cm, 2.1 * cm, 2.1 * cm, 8.8 * cm, 2.8 * cm], fonte=7))
    else:
        elementos.append(_paragrafo("Verificação de eficácia ainda não programada.", estilos["normal"]))

    elementos.append(titulo_secao(6, "Anexos"))
    evidencias = dados.get("evidencias", [])
    if evidencias:
        linhas = [[
            Paragraph("Etapa", estilos["cabecalho"]),
            Paragraph("Arquivo", estilos["cabecalho"]),
            Paragraph("Descrição", estilos["cabecalho"]),
            Paragraph("Enviado por", estilos["cabecalho"]),
            Paragraph("Data", estilos["cabecalho"]),
        ]]
        for evidencia in evidencias:
            linhas.append(
                [
                    _paragrafo(ROTULOS_ETAPA.get(evidencia.get("etapa"), evidencia.get("etapa")), estilos["pequeno"]),
                    _paragrafo(evidencia.get("nome_original"), estilos["pequeno"]),
                    _paragrafo(evidencia.get("descricao"), estilos["pequeno"]),
                    _paragrafo(evidencia.get("enviado_por_nome"), estilos["pequeno"]),
                    _paragrafo(_data(evidencia.get("criado_em"), True), estilos["pequeno"]),
                ]
            )
        elementos.append(tabela(linhas, [2.5 * cm, 4.4 * cm, 4.4 * cm, 3.4 * cm, 2.3 * cm], fonte=6.8))
    else:
        elementos.append(_paragrafo("Nenhum anexo registrado.", estilos["normal"]))

    elementos.append(CondPageBreak(3.5 * cm))
    elementos.append(titulo_secao(7, "Histórico da ACR"))
    historico = dados.get("historico", [])
    if historico:
        linhas = [[
            Paragraph("Data", estilos["cabecalho"]),
            Paragraph("Evento", estilos["cabecalho"]),
            Paragraph("Etapa", estilos["cabecalho"]),
            Paragraph("Usuário", estilos["cabecalho"]),
            Paragraph("Detalhes", estilos["cabecalho"]),
        ]]
        for evento in historico:
            linhas.append(
                [
                    _paragrafo(_data(evento.get("criado_em"), True), estilos["pequeno"]),
                    _paragrafo(evento.get("evento"), estilos["pequeno"]),
                    _paragrafo(ROTULOS_ETAPA.get(evento.get("etapa"), evento.get("etapa")), estilos["pequeno"]),
                    _paragrafo(evento.get("usuario"), estilos["pequeno"]),
                    _paragrafo(evento.get("justificativa"), estilos["pequeno"]),
                ]
            )
        elementos.append(tabela(linhas, [2.5 * cm, 3.4 * cm, 2.7 * cm, 3.4 * cm, 5 * cm], fonte=6.8))
    else:
        elementos.append(_paragrafo("Nenhum evento registrado.", estilos["normal"]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

from datetime import datetime
from html import escape
from io import BytesIO


LARANJA = "#F36B21"
CINZA_ESCURO = "#4B5055"
CINZA = "#6C757D"
CINZA_CLARO = "#F2F3F4"


def _texto(valor, padrao="-"):
    if valor is None or valor == "":
        return padrao
    return str(valor)


def _data(valor):
    if not valor:
        return "-"
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _hora(valor):
    if not valor:
        return "-"
    if hasattr(valor, "total_seconds"):
        segundos = int(valor.total_seconds())
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}"
    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M")
    return str(valor)[:5]


def gerar_pdf_hora_seguranca(registro, itens):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.6 * cm,
        title=f"Hora de Segurança {registro.get('id', '')}",
        author="TrackPlan",
        subject="Relatório de Hora de Segurança",
    )

    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "TituloHS",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloHS",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor(CINZA),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "secao": ParagraphStyle(
            "SecaoHS",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(LARANJA),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "NormalHS",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10.5,
            textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_LEFT,
        ),
        "rotulo": ParagraphStyle(
            "RotuloHS",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor(CINZA),
        ),
        "cabecalho": ParagraphStyle(
            "CabecalhoHS",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            textColor=colors.white,
        ),
    }

    def paragrafo(valor, estilo, padrao="-"):
        conteudo = escape(_texto(valor, padrao)).replace("\n", "<br/>")
        return Paragraph(conteudo, estilo)

    def decorar_pagina(canvas, documento):
        canvas.saveState()
        largura, _ = A4
        canvas.setStrokeColor(colors.HexColor(LARANJA))
        canvas.setLineWidth(1.1)
        canvas.line(doc.leftMargin, 1.1 * cm, largura - doc.rightMargin, 1.1 * cm)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            doc.leftMargin,
            0.68 * cm,
            f"TrackPlan - Hora de Segurança | Gerado em {gerado_em}",
        )
        canvas.drawRightString(
            largura - doc.rightMargin,
            0.68 * cm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    elementos = [
        Paragraph("RELATÓRIO DE HORA DE SEGURANÇA", estilos["titulo"]),
        Paragraph(
            f"Registro #{escape(_texto(registro.get('id')))}",
            estilos["subtitulo"],
        ),
        Paragraph("1. Identificação", estilos["secao"]),
    ]

    identificacao = [
        [
            paragrafo("Data", estilos["rotulo"]),
            paragrafo(_data(registro.get("data")), estilos["normal"]),
            paragrafo("Hora / turno", estilos["rotulo"]),
            paragrafo(
                f"{_hora(registro.get('hora'))} - {_texto(registro.get('turno'))}",
                estilos["normal"],
            ),
        ],
        [
            paragrafo("Auditor", estilos["rotulo"]),
            paragrafo(registro.get("nome_auditor"), estilos["normal"]),
            paragrafo("Matrícula", estilos["rotulo"]),
            paragrafo(registro.get("matricula_auditor"), estilos["normal"]),
        ],
        [
            paragrafo("Tema", estilos["rotulo"]),
            paragrafo(registro.get("nome_tema"), estilos["normal"]),
            paragrafo("Local", estilos["rotulo"]),
            paragrafo(registro.get("local"), estilos["normal"]),
        ],
        [
            paragrafo("Centro de custos", estilos["rotulo"]),
            paragrafo(
                f"{_texto(registro.get('centro_codigo'))} - "
                f"{_texto(registro.get('centro_descricao'))}",
                estilos["normal"],
            ),
            paragrafo("Participantes", estilos["rotulo"]),
            paragrafo(registro.get("nomes_participantes"), estilos["normal"]),
        ],
    ]
    tabela_identificacao = Table(
        identificacao,
        colWidths=[2.5 * cm, 6.0 * cm, 2.5 * cm, 6.0 * cm],
    )
    tabela_identificacao.setStyle(
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
    elementos.extend(
        [
            tabela_identificacao,
            Spacer(1, 0.15 * cm),
        ]
    )
    if registro.get("observacoes_gerais"):
        elementos.extend([
            Paragraph("Observações gerais", estilos["secao"]),
            paragrafo(registro.get("observacoes_gerais"), estilos["normal"]),
            Spacer(1, 0.15 * cm),
        ])
    elementos.append(Paragraph("2. Itens de verificação", estilos["secao"]))

    linhas = [[
        Paragraph("#", estilos["cabecalho"]),
        Paragraph("Item", estilos["cabecalho"]),
        Paragraph("Resultado", estilos["cabecalho"]),
        Paragraph("Desvio / ação", estilos["cabecalho"]),
        Paragraph("Prazo", estilos["cabecalho"]),
    ]]
    for indice, item in enumerate(itens, start=1):
        detalhes = item.get("descricao_desvio") or ""
        if item.get("descricao_acao"):
            detalhes += ("\n" if detalhes else "") + f"Ação: {item['descricao_acao']}"
        linhas.append(
            [
                paragrafo(indice, estilos["normal"]),
                paragrafo(item.get("texto"), estilos["normal"]),
                paragrafo(item.get("resultado"), estilos["normal"]),
                paragrafo(detalhes, estilos["normal"]),
                paragrafo(_data(item.get("prazo_acao")), estilos["normal"]),
            ]
        )

    tabela_itens = Table(
        linhas,
        colWidths=[0.7 * cm, 7.2 * cm, 2.0 * cm, 5.2 * cm, 1.9 * cm],
        repeatRows=1,
    )
    comandos = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LARANJA)),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for linha in range(1, len(linhas)):
        if linha % 2 == 0:
            comandos.append(
                ("BACKGROUND", (0, linha), (-1, linha), colors.HexColor("#FAFAFA"))
            )
    tabela_itens.setStyle(TableStyle(comandos))
    elementos.append(tabela_itens)

    total_nc = sum(1 for item in itens if item.get("resultado") == "NC")
    elementos.extend(
        [
            Spacer(1, 0.25 * cm),
            paragrafo(
                f"Resumo: {len(itens)} item(ns) verificado(s), "
                f"{total_nc} não conformidade(s).",
                estilos["normal"],
            ),
        ]
    )

    adicionais = registro.get("itens_adicionais") or []
    if adicionais:
        elementos.append(Paragraph("3. Outros itens identificados", estilos["secao"]))
        linhas_adicionais = [[
            Paragraph("Tipo", estilos["cabecalho"]),
            Paragraph("Item", estilos["cabecalho"]),
            Paragraph("Situação observada", estilos["cabecalho"]),
            Paragraph("Ação / prazo", estilos["cabecalho"]),
        ]]
        for adicional in adicionais:
            acao = adicional.get("descricao_acao") or "Sem ação gerada"
            if adicional.get("prazo"):
                acao += f"\nPrazo: {_data(adicional.get('prazo'))}"
            linhas_adicionais.append([
                paragrafo(_texto(adicional.get("tipo")).title(), estilos["normal"]),
                paragrafo(adicional.get("item_verificacao"), estilos["normal"]),
                paragrafo(adicional.get("descricao_situacao"), estilos["normal"]),
                paragrafo(acao, estilos["normal"]),
            ])
        tabela_adicionais = Table(
            linhas_adicionais,
            colWidths=[2.3 * cm, 4.8 * cm, 5.5 * cm, 4.4 * cm],
            repeatRows=1,
        )
        tabela_adicionais.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LARANJA)),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabela_adicionais)

    doc.build(
        elementos,
        onFirstPage=decorar_pagina,
        onLaterPages=decorar_pagina,
    )
    buffer.seek(0)
    return buffer

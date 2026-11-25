from datetime import datetime
from html import escape
from io import BytesIO
from zoneinfo import ZoneInfo


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


def _acao_resumida(valor):
    texto = _texto(valor)
    marcador = "\n\nAção: "
    return texto.split(marcador, 1)[-1] if marcador in texto else texto


def gerar_pdf_ifs_cliente(inspecao, desvios):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    gerado_em = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.6 * cm,
        title=f"Relatório IFS do Cliente #{inspecao.get('id', '')}",
        author="TrackPlan",
        subject="Relatório de IFS do Cliente",
    )

    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "TituloIFSCliente", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloIFSCliente", parent=base["Normal"], fontSize=9,
            leading=12, textColor=colors.HexColor(CINZA), alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "secao": ParagraphStyle(
            "SecaoIFSCliente", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=colors.HexColor(LARANJA),
            spaceBefore=9, spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "NormalIFSCliente", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10.2, textColor=colors.HexColor(CINZA_ESCURO),
            alignment=TA_LEFT,
        ),
        "rotulo": ParagraphStyle(
            "RotuloIFSCliente", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9, textColor=colors.HexColor(CINZA),
        ),
        "cabecalho": ParagraphStyle(
            "CabecalhoIFSCliente", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7, leading=8.5, textColor=colors.white,
        ),
    }

    def p(valor, estilo="normal", padrao="-"):
        conteudo = escape(_texto(valor, padrao)).replace("\n", "<br/>")
        return Paragraph(conteudo, estilos[estilo])

    def tabela(dados, larguras, cabecalho=False):
        resultado = Table(dados, colWidths=larguras, repeatRows=1 if cabecalho else 0)
        comandos = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if cabecalho:
            comandos.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LARANJA)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ])
        else:
            comandos.extend([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(CINZA_CLARO)),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(CINZA_CLARO)),
            ])
        resultado.setStyle(TableStyle(comandos))
        return resultado

    def rodape(canvas, documento):
        canvas.saveState()
        largura, _ = A4
        canvas.setStrokeColor(colors.HexColor(LARANJA))
        canvas.setLineWidth(1)
        canvas.line(doc.leftMargin, 1.08 * cm, largura - doc.rightMargin, 1.08 * cm)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(doc.leftMargin, 0.66 * cm, f"TrackPlan - IFS do Cliente | Gerado em {gerado_em}")
        canvas.drawRightString(largura - doc.rightMargin, 0.66 * cm, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    centro = " - ".join(
        parte for parte in (
            _texto(inspecao.get("centro_codigo"), ""),
            _texto(inspecao.get("centro_descricao"), ""),
        ) if parte
    ) or "-"
    status = {
        "sem_desvios": "Sem desvios", "em_tratamento": "Em tratamento",
        "pronta_devolutiva": "Pronta para devolutiva", "encerrada": "Encerrada",
    }.get(inspecao.get("status"), _texto(inspecao.get("status")))

    elementos = [
        Paragraph("RELATÓRIO DE IFS DO CLIENTE", estilos["titulo"]),
        Paragraph(f"Registro #{escape(_texto(inspecao.get('id')))}", estilos["subtitulo"]),
        Paragraph("1. Identificação da inspeção", estilos["secao"]),
    ]
    identificacao = [
        [p("Data", "rotulo"), p(_data(inspecao.get("data_inspecao"))), p("Hora", "rotulo"), p(_hora(inspecao.get("hora_inspecao")))],
        [p("Referência do cliente", "rotulo"), p(inspecao.get("referencia_cliente")), p("Local", "rotulo"), p(inspecao.get("local_inspecao"))],
        [p("Centro de custos", "rotulo"), p(centro), p("Gerência", "rotulo"), p(inspecao.get("gerencia"))],
        [p("Administrador do contrato", "rotulo"), p(inspecao.get("administrador_contrato")), p("Contratada", "rotulo"), p(inspecao.get("contratada"))],
        [p("Profissional do SESMT (contratada) / Liderança", "rotulo"), p(inspecao.get("profissional_sesmt_contratada_lideranca")), p("SESMT (Gerdau / Fiscalizadora)", "rotulo"), p(inspecao.get("sesmt_gerdau_fiscalizadora"))],
        [p("Participantes", "rotulo"), p(inspecao.get("participantes")), p("Registrado por", "rotulo"), p(inspecao.get("criado_por_nome"))],
        [p("Atividade / OS", "rotulo"), p(inspecao.get("descricao_atividade_os")), "", ""],
    ]
    tabela_identificacao = tabela(identificacao, [3.1 * cm, 5.6 * cm, 3.1 * cm, 5.6 * cm])
    tabela_identificacao.setStyle(TableStyle([("SPAN", (1, 6), (3, 6))]))
    elementos.extend([tabela_identificacao, Paragraph("2. Resultado", estilos["secao"])])

    resultado = [[
        p("Nota", "cabecalho"), p("Conceito", "cabecalho"),
        p("Itens avaliados", "cabecalho"), p("Não conformidades", "cabecalho"),
        p("Situação", "cabecalho"),
    ], [
        p(f"{float(inspecao.get('percentual') or 0):.2f}%"), p(inspecao.get("conceito")),
        p(inspecao.get("total_itens_avaliados")), p(inspecao.get("total_nao_conformidades")), p(status),
    ]]
    elementos.extend([tabela(resultado, [2.6 * cm, 3.5 * cm, 3.2 * cm, 3.5 * cm, 4.6 * cm], True), Paragraph("3. Não conformidades e planos de ação", estilos["secao"])])

    if not desvios:
        elementos.append(p("Esta inspeção não possui não conformidades."))
    for desvio in desvios:
        elementos.extend([
            p(f"Item {desvio.get('codigo_item')} - {desvio.get('descricao_item')}", "rotulo"),
            p(
                f"{('Potencial ' + desvio.get('potencial')) if desvio.get('potencial') else 'Sem potencial'}"
                f" | Não conformidade: {desvio.get('desvio_observado') or '-'}"
            ),
            Spacer(1, 0.1 * cm),
        ])
        linhas = [[p("Ação", "cabecalho"), p("Responsável", "cabecalho"), p("Prazo", "cabecalho"), p("Situação", "cabecalho")]]
        for acao in desvio.get("acoes") or []:
            linhas.append([
                p(_acao_resumida(acao.get("acao_descricao"))), p(acao.get("responsavel_nome")),
                p(_data(acao.get("prazo"))), p(acao.get("acao_status")),
            ])
        if len(linhas) == 1:
            linhas.append([p("Nenhuma ação vinculada."), "", "", ""])
        tabela_acoes = tabela(linhas, [8.2 * cm, 3.8 * cm, 2.2 * cm, 4.2 * cm], True)
        if len(linhas) == 2 and not (desvio.get("acoes") or []):
            tabela_acoes.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
        elementos.extend([tabela_acoes, Spacer(1, 0.22 * cm)])

    doc.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    buffer.seek(0)
    return buffer

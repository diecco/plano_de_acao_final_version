from datetime import datetime
from html import escape
from io import BytesIO
import os


LARANJA = "#F36B21"
CINZA_ESCURO = "#4B5055"
CINZA = "#6C757D"
CINZA_CLARO = "#F2F3F4"


def _texto(valor, padrao="-"):
    return padrao if valor is None or valor == "" else str(valor)


def _data(valor, hora=False):
    if not valor:
        return "-"
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y %H:%M" if hora else "%d/%m/%Y")
    return str(valor)


def _moeda(valor):
    if valor is None:
        return "-"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_book_ressarcimento(processo, orcamentos, anexos, historico, logo_path=None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.utils import ImageReader
    from pypdf import PdfReader, PdfWriter

    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    buffer_principal = BytesIO()
    doc = SimpleDocTemplate(
        buffer_principal, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.6 * cm,
        title=f"Book de Ressarcimento {processo.get('numero', '')}",
        author="TrackPlan", subject="Processo de Ressarcimento PCP-M",
    )
    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle("TituloBook", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor(CINZA_ESCURO), alignment=TA_CENTER, spaceAfter=4),
        "subtitulo": ParagraphStyle("SubtituloBook", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.HexColor(CINZA), alignment=TA_CENTER, spaceAfter=12),
        "secao": ParagraphStyle("SecaoBook", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor(LARANJA), spaceBefore=10, spaceAfter=6),
        "normal": ParagraphStyle("NormalBook", parent=base["Normal"], fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=colors.HexColor(CINZA_ESCURO), alignment=TA_LEFT),
        "pequeno": ParagraphStyle("PequenoBook", parent=base["Normal"], fontName="Helvetica", fontSize=7.2, leading=9, textColor=colors.HexColor(CINZA_ESCURO)),
        "cabecalho": ParagraphStyle("CabecalhoBook", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white),
    }

    def p(valor, estilo="normal", padrao="-"):
        return Paragraph(escape(_texto(valor, padrao)).replace("\n", "<br/>"), estilos[estilo])

    def tabela(linhas, larguras, cabecalho=False):
        item = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0, hAlign="LEFT")
        comandos = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DADD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if cabecalho:
            comandos.extend([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LARANJA)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)])
        for linha in range(1 if cabecalho else 0, len(linhas)):
            if linha % 2 == 0:
                comandos.append(("BACKGROUND", (0, linha), (-1, linha), colors.HexColor("#FAFAFA")))
        item.setStyle(TableStyle(comandos))
        return item

    def rodape(canvas, documento):
        canvas.saveState()
        largura, _ = A4
        canvas.setStrokeColor(colors.HexColor(LARANJA)); canvas.setLineWidth(1)
        canvas.line(doc.leftMargin, 1.05 * cm, largura - doc.rightMargin, 1.05 * cm)
        canvas.setFillColor(colors.HexColor(CINZA)); canvas.setFont("Helvetica", 7)
        canvas.drawString(doc.leftMargin, 0.65 * cm, f"TrackPlan - Ressarcimentos | Gerado em {gerado_em}")
        canvas.drawRightString(largura - doc.rightMargin, 0.65 * cm, f"Página {documento.page}")
        canvas.restoreState()

    elementos = []
    if logo_path and os.path.isfile(logo_path):
        logo = Image(logo_path, width=3.1 * cm, height=1.25 * cm); logo.hAlign = "CENTER"; elementos.append(logo)
    elementos.extend([p("BOOK DE RESSARCIMENTO", "titulo"), p(processo.get("numero"), "subtitulo")])
    elementos.append(p("1. Identificação do processo", "secao"))
    elementos.append(tabela([
        [p("Processo", "pequeno"), p(processo.get("numero")), p("Centro de custos", "pequeno"), p(f"{processo.get('centro_codigo', '')} - {processo.get('centro_descricao', '')}")],
        [p("Equipamento", "pequeno"), p(processo.get("equipamento_snapshot")), p("Empresa da ocorrência", "pequeno"), p(processo.get("empresa_ocorrencia_snapshot"))],
        [p("Data e hora", "pequeno"), p(_data(processo.get("ocorrencia_em"), True)), p("Status", "pequeno"), p(processo.get("status_processo"))],
    ], [3.1 * cm, 6.0 * cm, 3.1 * cm, 6.0 * cm]))
    elementos.append(p("Descrição da ocorrência", "secao")); elementos.append(p(processo.get("descricao_ocorrencia")))
    elementos.append(p("Pessoas envolvidas", "secao"))
    elementos.append(tabela([
        [p("Operador", "pequeno"), p(processo.get("operador_nome_snapshot")), p("Matrícula", "pequeno"), p(processo.get("operador_matricula_snapshot"))],
        [p("Funcionário Tradimaq", "pequeno"), p(processo.get("funcionario_nome_snapshot")), p("Matrícula", "pequeno"), p(processo.get("funcionario_matricula_snapshot"))],
    ], [3.3 * cm, 6.3 * cm, 2.5 * cm, 6.1 * cm]))
    elementos.append(p("2. Cliente e aprovador", "secao"))
    elementos.append(tabela([
        [p("Empresa", "pequeno"), p(processo.get("empresa_cliente_snapshot")), p("Centro de custos", "pequeno"), p(processo.get("cliente_centro_custos"))],
        [p("Área", "pequeno"), p(processo.get("cliente_area")), p("E-mail", "pequeno"), p(processo.get("aprovador_email"))],
        [p("Telefone", "pequeno"), p(processo.get("aprovador_telefone")), "", ""],
    ], [3.1 * cm, 6.0 * cm, 3.1 * cm, 6.0 * cm]))
    elementos.append(p("3. Orçamentos TOTVS", "secao"))
    linhas_orcamentos = [[p("Versão", "cabecalho"), p("Número", "cabecalho"), p("Valor", "cabecalho"), p("Envio", "cabecalho"), p("Status", "cabecalho")]]
    for item in orcamentos:
        linhas_orcamentos.append([p(f"V{item['versao']}", "pequeno"), p(item.get("numero_orcamento_totvs"), "pequeno"), p(_moeda(item.get("valor_orcamento")), "pequeno"), p(_data(item.get("data_envio")), "pequeno"), p(item.get("status"), "pequeno")])
    elementos.append(tabela(linhas_orcamentos, [1.7 * cm, 5.0 * cm, 3.2 * cm, 3.2 * cm, 5.1 * cm], True))

    fotos = [a for a in anexos if a.get("categoria") == "foto_avaria" and a.get("caminho_absoluto") and os.path.isfile(a["caminho_absoluto"])]
    if fotos:
        elementos.extend([PageBreak(), p("4. Registro fotográfico da avaria", "secao")])
        for indice, foto in enumerate(fotos, 1):
            try:
                leitor = ImageReader(foto["caminho_absoluto"]); largura, altura = leitor.getSize()
                escala = min((17.5 * cm) / largura, (20 * cm) / altura)
                imagem = Image(foto["caminho_absoluto"], width=largura * escala, height=altura * escala); imagem.hAlign = "CENTER"
                elementos.extend([p(f"Foto {indice} - {foto.get('nome_original')}", "pequeno"), Spacer(1, 0.15 * cm), imagem, Spacer(1, 0.4 * cm)])
            except Exception:
                elementos.append(p(f"Não foi possível renderizar: {foto.get('nome_original')}", "pequeno"))
    else:
        elementos.append(p("4. Registro fotográfico da avaria", "secao"))
        elementos.append(p("Nenhuma foto ativa foi localizada para incorporação ao book."))

    elementos.extend([PageBreak(), p("5. Relação de documentos", "secao")])
    linhas_anexos = [[p("Categoria", "cabecalho"), p("Arquivo", "cabecalho"), p("Incluído em", "cabecalho")]]
    for item in anexos:
        linhas_anexos.append([p(item.get("categoria", "").replace("_", " ").title(), "pequeno"), p(item.get("nome_original"), "pequeno"), p(_data(item.get("criado_em"), True), "pequeno")])
    elementos.append(tabela(linhas_anexos, [4.2 * cm, 9.6 * cm, 4.4 * cm], True))
    elementos.append(p("6. Histórico", "secao"))
    linhas_historico = [[p("Data", "cabecalho"), p("Evento", "cabecalho"), p("Descrição", "cabecalho"), p("Usuário", "cabecalho")]]
    for item in historico:
        linhas_historico.append([p(_data(item.get("criado_em"), True), "pequeno"), p(item.get("evento"), "pequeno"), p(item.get("descricao"), "pequeno"), p(item.get("usuario_nome"), "pequeno")])
    elementos.append(tabela(linhas_historico, [3.2 * cm, 3.8 * cm, 7.2 * cm, 4.0 * cm], True))
    doc.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    buffer_principal.seek(0)

    escritor = PdfWriter()
    escritor.append(PdfReader(buffer_principal))
    for anexo in anexos:
        caminho = anexo.get("caminho_absoluto")
        if not caminho or not os.path.isfile(caminho) or anexo.get("categoria") == "foto_avaria":
            continue
        extensao = os.path.splitext(caminho)[1].lower()
        try:
            if extensao == ".pdf":
                leitor = PdfReader(caminho)
                if leitor.is_encrypted:
                    try:
                        leitor.decrypt("")
                    except Exception:
                        continue
                escritor.append(leitor)
            elif extensao in {".jpg", ".jpeg", ".png"}:
                pagina_imagem = BytesIO()
                doc_imagem = SimpleDocTemplate(pagina_imagem, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.6 * cm)
                leitor_imagem = ImageReader(caminho); largura, altura = leitor_imagem.getSize()
                escala = min((17.5 * cm) / largura, (23.5 * cm) / altura)
                imagem = Image(caminho, width=largura * escala, height=altura * escala); imagem.hAlign = "CENTER"
                doc_imagem.build([p(f"Anexo - {anexo.get('nome_original')}", "secao"), Spacer(1, 0.3 * cm), imagem], onFirstPage=rodape)
                pagina_imagem.seek(0); escritor.append(PdfReader(pagina_imagem))
        except Exception:
            continue
    resultado = BytesIO(); escritor.write(resultado); resultado.seek(0)
    return resultado

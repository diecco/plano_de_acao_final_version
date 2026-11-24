import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, time
from io import BytesIO

from openpyxl import load_workbook


class RelatoOcorrenciaImportError(ValueError):
    pass


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _identifier(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = _text(value)
    return text[:-2] if text.endswith(".0") and text[:-2].isdigit() else text


def _normalized(value):
    text = unicodedata.normalize("NFKD", _text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def _header_key(value):
    return _normalized(value).split(" - relato de ocorrencia", 1)[0].strip()


def _parse_date(value, field_name):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    raise RelatoOcorrenciaImportError(f"{field_name} inválida: {text}")


def _parse_time(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, time):
        return value.replace(microsecond=0)
    if isinstance(value, float) and 0 <= value < 1:
        seconds = round(value * 24 * 60 * 60)
        return time((seconds // 3600) % 24, (seconds % 3600) // 60, seconds % 60)
    text = _text(value)
    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, pattern).time()
        except ValueError:
            pass
    raise RelatoOcorrenciaImportError(f"Hora da ocorrência inválida: {text}")


def _parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    if isinstance(value, date):
        return datetime.combine(value, time())
    text = _text(value)
    for pattern in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    return None


def _split_lines(value):
    # Os campos-filhos do Fluig aparecem com quebra de linha em algumas
    # exportações e separados por ponto e vírgula em outras.
    return [
        part.strip()
        for part in re.split(r"[;\r\n]+", _text(value))
        if part.strip()
    ]


def _extract_cost_center(value):
    text = _text(value)
    match = re.search(r"\b\d+(?:\.\d+){2,}\b", text)
    return match.group(0) if match else text[:100]


def _json_value(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return value


def _build_involved(value):
    columns = {
        "nome": _split_lines(value("responsavelenvolvido")),
        "matricula": _split_lines(value("matricularesponsavelenvolvido")),
        "email": _split_lines(value("emailresponsavelenvolvido")),
        "centro_custos": _split_lines(value("centrodecustoenvolvido")),
        "descricao": _split_lines(value("envolvidos")),
    }
    count = max((len(items) for items in columns.values()), default=0)
    return [
        {
            key: items[index] if index < len(items) else None
            for key, items in columns.items()
        }
        for index in range(count)
    ]


def parse_fluig_relatos_ocorrencias(file_bytes):
    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:
        raise RelatoOcorrenciaImportError(
            "O arquivo não é uma planilha Excel válida."
        ) from exc
    if not workbook.worksheets:
        raise RelatoOcorrenciaImportError("A planilha não possui abas.")

    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [_text(value) for value in next(rows)]
    except StopIteration as exc:
        raise RelatoOcorrenciaImportError("A planilha está vazia.") from exc

    positions = {}
    for index, header in enumerate(headers):
        positions.setdefault(_header_key(header), index)

    required = {
        "solicitacao",
        "situacao",
        "dataocorrencia",
        "descricaoocorrencia",
        "ocorrencia",
    }
    if not required.issubset(positions):
        raise RelatoOcorrenciaImportError(
            "O arquivo não corresponde à exportação de Relato de Ocorrência do Fluig."
        )

    records = []
    errors = []
    seen = set()
    for excel_row, row in enumerate(rows, start=2):
        if not any(_text(cell) for cell in row if cell is not None):
            continue

        def value(name):
            position = positions.get(_normalized(name))
            return row[position] if position is not None and position < len(row) else None

        try:
            request_number = _identifier(value("solicitacao"))
            if not request_number:
                raise RelatoOcorrenciaImportError("Solicitação não informada")
            if request_number in seen:
                raise RelatoOcorrenciaImportError("Solicitação duplicada no arquivo")
            seen.add(request_number)

            occurrence_date = _parse_date(value("dataocorrencia"), "Data da ocorrência")
            if not occurrence_date:
                raise RelatoOcorrenciaImportError("Data da ocorrência não informada")
            occurrence_type = _text(value("ocorrencia"))
            if not occurrence_type:
                raise RelatoOcorrenciaImportError("Tipo do relato não informado")
            description = _text(value("descricaoocorrencia"))
            if not description:
                raise RelatoOcorrenciaImportError("Descrição da ocorrência não informada")

            raw = {
                header: _json_value(row[index] if index < len(row) else None)
                for index, header in enumerate(headers)
                if header
            }
            cost_center_raw = _text(value("centrocustoocorrencia"))
            record = {
                "solicitacao": request_number,
                "situacao_fluig": _text(value("situacao")),
                "requisitante_identificador": _text(value("matricula requisitante")),
                "requisitante_nome": _text(value("requisitante")),
                "localizacao_fluxo": _text(value("localizacao")),
                "responsavel_fluxo": _text(value("responsavel")),
                "inicio_em": _parse_datetime(value("inicio")),
                "fim_em": _parse_datetime(value("fim")),
                "acao_tomada": _text(value("acaotomada")),
                "area_ocorrencia": _text(value("areaocorrencia")),
                "centro_custos_original": cost_center_raw,
                "centro_custos_codigo": _extract_cost_center(cost_center_raw),
                "classificacao_ocorrencia": _text(value("classificacaoocorrencia")),
                "data_ocorrencia": occurrence_date,
                "hora_ocorrencia": _parse_time(value("horaocorrencia")),
                "descricao_ocorrencia": description,
                "local_ocorrencia": _text(value("localocorrencia")),
                "responsavel_registro": _text(value("nomeresponsavelregistro")),
                "tipo_relato": occurrence_type,
                "tipo_origem": _text(value("tipoocorrencia")),
                "turno": _text(value("turno")),
                "responsavel_turno": _text(value("responsaveldoturno")),
                "membros_atingidos": _text(value("membrosatingidos")),
                "envolvidos": _build_involved(value),
                "dados_origem": raw,
            }
            payload = json.dumps(record, ensure_ascii=False, default=str, sort_keys=True)
            record["conteudo_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            records.append(record)
        except RelatoOcorrenciaImportError as exc:
            errors.append({
                "linha": excel_row,
                "solicitacao": _identifier(value("solicitacao")),
                "erro": str(exc),
            })

    if not records:
        raise RelatoOcorrenciaImportError(
            "Nenhum relato válido foi encontrado na planilha."
        )
    return records, errors

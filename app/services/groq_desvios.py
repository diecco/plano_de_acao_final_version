import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
LOGGER = logging.getLogger(__name__)


class AnaliseIAError(RuntimeError):
    pass


def _detalhes_erro_http(exc):
    """Extrai apenas metadados seguros da resposta de erro do Groq."""
    codigo = ""
    mensagem = ""
    try:
        corpo = json.loads(exc.read().decode("utf-8", errors="replace"))
        erro = corpo.get("error") or {}
        if isinstance(erro, dict):
            codigo = _texto(erro.get("code") or erro.get("type"), 100)
            mensagem = _texto(erro.get("message"), 500)
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        pass
    request_id = ""
    if getattr(exc, "headers", None):
        request_id = _texto(
            exc.headers.get("x-request-id") or exc.headers.get("request-id"), 100
        )
    return codigo, mensagem, request_id


def _texto(valor, limite):
    return " ".join(str(valor or "").split())[:limite]


def _montar_requisicao(api_key, payload):
    return Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Evita que a camada de proteção da API trate a chamada como um
            # cliente genérico do urllib antes de encaminhá-la ao Groq.
            "User-Agent": "TrackPlan/1.0 (Groq API client)",
        },
        method="POST",
    )


def _extrair_json(conteudo):
    """Extrai o primeiro objeto JSON válido, mesmo quando vier cercado por texto."""
    if not isinstance(conteudo, str):
        raise AnaliseIAError("A IA devolveu uma resposta inválida.")

    texto = conteudo.strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        if linhas and linhas[0].strip().lower() in {"```", "```json"}:
            linhas = linhas[1:]
        if linhas and linhas[-1].strip() == "```":
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        decodificador = json.JSONDecoder()
        for indice, caractere in enumerate(texto):
            if caractere != "{":
                continue
            try:
                resultado, _ = decodificador.raw_decode(texto[indice:])
                return resultado
            except json.JSONDecodeError:
                continue
    raise AnaliseIAError("A IA devolveu uma resposta que não pôde ser validada.")


def _ler_resultado(resposta, modelo):
    bruto = json.loads(resposta.read().decode("utf-8"))
    conteudo = bruto["choices"][0]["message"]["content"]
    resultado = _validar_resposta(_extrair_json(conteudo))
    resultado["modelo"] = bruto.get("model") or modelo
    return resultado


def _validar_resposta(resultado):
    if not isinstance(resultado, dict):
        raise AnaliseIAError("A IA devolveu uma resposta inválida.")

    estado = resultado.get("estado")
    if estado not in {"concluida", "precisa_complementacao"}:
        raise AnaliseIAError("A IA não informou o estado da análise.")

    perguntas = resultado.get("perguntas") or []
    if not isinstance(perguntas, list):
        perguntas = []
    resultado["perguntas"] = [
        _texto(pergunta, 300) for pergunta in perguntas[:4] if _texto(pergunta, 300)
    ]

    if estado == "concluida":
        if resultado.get("severidade_sugerida") not in {"A", "B", "C"}:
            raise AnaliseIAError("A IA não retornou uma severidade válida.")
        if resultado.get("probabilidade_sugerida") not in {"baixa", "media", "alta"}:
            raise AnaliseIAError("A IA não retornou uma probabilidade válida.")
        for campo in ("exposicao_sugerida", "controles_sugeridos", "ocorrencia_sugerida"):
            if resultado.get(campo) not in {"baixa", "media", "alta"}:
                raise AnaliseIAError("A IA não retornou os fatores da probabilidade.")
        resultado["redacao_sugerida"] = _texto(resultado.get("redacao_sugerida"), 4000)
        resultado["justificativa"] = _texto(resultado.get("justificativa"), 1200)
        if not resultado["redacao_sugerida"] or not resultado["justificativa"]:
            raise AnaliseIAError("A sugestão da IA veio incompleta.")
        try:
            resultado["confianca"] = max(0, min(100, int(resultado.get("confianca", 0))))
        except (TypeError, ValueError):
            resultado["confianca"] = 0
    return resultado


def analisar_desvio(dados):
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise AnaliseIAError("A análise por IA ainda não foi configurada.")

    modelo = os.environ.get("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    contexto = {
        "tipo": _texto(dados.get("tipo"), 30),
        "categoria": _texto(dados.get("categoria"), 120),
        "setor": _texto(dados.get("setor"), 120),
        "descricao": _texto(dados.get("descricao"), 4000),
        "respostas_complementares": dados.get("respostas_complementares") or [],
    }
    sistema = """
Você auxilia um profissional de SSMA a registrar relatos de desvios. Não tome a
decisão final e não invente fatos. Melhore a redação em português do Brasil de
forma objetiva, preservando integralmente o sentido do relato. Avalie a
consequência máxima razoavelmente plausível: A para fatalidade, incapacidade
permanente, múltiplas vítimas ou perda catastrófica; B para lesão com
afastamento, fratura, internação, incapacidade temporária relevante ou dano
significativo; C para primeiros socorros, sem afastamento ou dano leve.
Considere exposição baixa/rara, média/ocasional ou alta/frequente; controles
baixos significam adequados, médios significam parciais e altos significam
ausentes; e possibilidade de ocorrência baixa/improvável, média/possível ou
alta/provável. Calcule a probabilidade consolidada pela média dos três fatores:
até 1,5 baixa, até 2,3 média, acima disso alta. Se faltarem fatos capazes de
alterar a classificação, não classifique: retorne até quatro perguntas curtas,
objetivas e diretamente relevantes. Nunca solicite nome, matrícula, e-mail ou
outro dado pessoal. Quando o estado for precisa_complementacao, preencha os
campos de classificação e os textos ainda não definidos com string vazia e a
confiança com zero. Retorne somente JSON válido.
""".strip()
    schema = {
        "type": "object",
        "properties": {
            "estado": {"type": "string", "enum": ["concluida", "precisa_complementacao"]},
            "redacao_sugerida": {"type": "string"},
            "severidade_sugerida": {"type": "string", "enum": ["", "A", "B", "C"]},
            "probabilidade_sugerida": {"type": "string", "enum": ["", "baixa", "media", "alta"]},
            "exposicao_sugerida": {"type": "string", "enum": ["", "baixa", "media", "alta"]},
            "controles_sugeridos": {"type": "string", "enum": ["", "baixa", "media", "alta"]},
            "ocorrencia_sugerida": {"type": "string", "enum": ["", "baixa", "media", "alta"]},
            "justificativa": {"type": "string"},
            "confianca": {"type": "integer", "minimum": 0, "maximum": 100},
            "perguntas": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
        },
        "required": ["estado", "redacao_sugerida", "severidade_sugerida", "probabilidade_sugerida", "exposicao_sugerida", "controles_sugeridos", "ocorrencia_sugerida", "justificativa", "confianca", "perguntas"],
        "additionalProperties": False,
    }
    payload = {
        "model": modelo,
        "temperature": 0.1,
        "max_completion_tokens": 900,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": json.dumps(contexto, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "analise_desvio", "strict": True, "schema": schema},
        },
    }
    requisicao = _montar_requisicao(api_key, payload)
    try:
        with urlopen(requisicao, timeout=20) as resposta:
            return _ler_resultado(resposta, modelo)
    except HTTPError as exc:
        codigo, mensagem, request_id = _detalhes_erro_http(exc)
        LOGGER.error(
            "Falha HTTP na API Groq: status=%s codigo=%s request_id=%s mensagem=%s",
            exc.code,
            codigo or "nao_informado",
            request_id or "nao_informado",
            mensagem or "nao_informada",
        )
        if exc.code == 400 and codigo == "json_validate_failed":
            LOGGER.warning(
                "Groq recusou a saída estruturada; repetindo sem response_format e com validação local."
            )
            payload_fallback = dict(payload)
            payload_fallback.pop("response_format", None)
            payload_fallback["messages"] = [
                *payload["messages"],
                {
                    "role": "system",
                    "content": (
                        "A tentativa anterior falhou na serialização. Responda apenas com um "
                        "único objeto JSON, sem markdown, comentários ou texto antes/depois. "
                        "Use exatamente as chaves exigidas e valores compatíveis com as "
                        "instruções anteriores."
                    ),
                },
            ]
            try:
                with urlopen(
                    _montar_requisicao(api_key, payload_fallback), timeout=20
                ) as resposta:
                    return _ler_resultado(resposta, modelo)
            except HTTPError as fallback_exc:
                codigo, mensagem, request_id = _detalhes_erro_http(fallback_exc)
                LOGGER.error(
                    "Falha HTTP no fallback da API Groq: status=%s codigo=%s request_id=%s mensagem=%s",
                    fallback_exc.code,
                    codigo or "nao_informado",
                    request_id or "nao_informado",
                    mensagem or "nao_informada",
                )
                exc = fallback_exc
            except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as fallback_exc:
                raise AnaliseIAError(
                    "A IA devolveu uma resposta que não pôde ser validada."
                ) from fallback_exc
        if exc.code == 429:
            raise AnaliseIAError("O limite gratuito da IA foi atingido. Tente novamente mais tarde.") from exc
        if exc.code == 401:
            raise AnaliseIAError(
                "A credencial da IA foi recusada. Verifique a configuração no Render."
            ) from exc
        if exc.code == 403:
            raise AnaliseIAError(
                "A chamada à IA foi bloqueada antes de chegar ao modelo. Tente novamente; se persistir, consulte o log técnico do Render."
            ) from exc
        if exc.code == 404:
            raise AnaliseIAError(
                "O modelo de IA configurado não foi encontrado ou não está disponível."
            ) from exc
        if exc.code == 400:
            raise AnaliseIAError(
                "A solicitação enviada à IA foi recusada. Consulte o log técnico do Render."
            ) from exc
        if exc.code >= 500:
            raise AnaliseIAError(
                "O serviço de IA está temporariamente indisponível."
            ) from exc
        raise AnaliseIAError("Não foi possível concluir a análise por IA.") from exc
    except (URLError, TimeoutError) as exc:
        LOGGER.error(
            "Falha de conexão com a API Groq: tipo=%s motivo=%s",
            type(exc).__name__,
            _texto(getattr(exc, "reason", exc), 300),
        )
        raise AnaliseIAError("O serviço de IA está temporariamente indisponível.") from exc
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AnaliseIAError("A IA devolveu uma resposta que não pôde ser validada.") from exc

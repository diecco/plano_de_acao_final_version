import unittest
import importlib.util
import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class DesviosTests(unittest.TestCase):
    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for nome in (
            "desvios.html",
            "novo_desvio.html",
            "buffer_desvios.html",
            "detalhe_desvio.html",
        ):
            app.jinja_env.get_template(nome)

    def test_routes_are_registered(self):
        from app import create_app

        app = create_app()
        endpoints = {regra.endpoint for regra in app.url_map.iter_rules()}
        for endpoint in (
            "main.listar_desvios",
            "main.novo_desvio",
            "main.editar_desvio",
            "main.excluir_desvio",
            "main.buffer_desvios",
            "main.detalhar_desvio",
            "main.direcionar_desvio",
            "main.analisar_desvio_ia",
        ):
            self.assertIn(endpoint, endpoints)

    def test_severity_matrix_is_calculated_server_side(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "app" / "templates" / "novo_desvio.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("def _calcular_probabilidade", source)
        self.assertIn("def _calcular_risco", source)
        self.assertIn("A — Crítica", template)
        self.assertIn("B — Moderada", template)
        self.assertIn("C — Leve", template)

    def test_ai_analysis_is_optional_and_auditable(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(encoding="utf-8")
        service = (ROOT / "app" / "services" / "groq_desvios.py").read_text(encoding="utf-8")
        migration = (ROOT / "docs" / "evoluir_matriz_risco_desvios.sql").read_text(encoding="utf-8")
        self.assertIn("GROQ_API_KEY", service)
        self.assertIn("json_schema", service)
        self.assertIn("ia_utilizada", source)
        self.assertIn("ia_justificativa", migration)

    def test_groq_authentication_error_is_identified_and_logged(self):
        caminho = ROOT / "app" / "services" / "groq_desvios.py"
        spec = importlib.util.spec_from_file_location("groq_desvios_teste", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)

        resposta = BytesIO(
            b'{"error":{"message":"Invalid API Key","type":"invalid_request_error","code":"invalid_api_key"}}'
        )
        erro = HTTPError(
            "https://api.groq.com/openai/v1/chat/completions",
            401,
            "Unauthorized",
            {"x-request-id": "req-teste"},
            resposta,
        )
        with patch.dict("os.environ", {"GROQ_API_KEY": "segredo-teste"}), patch.object(
            modulo, "urlopen", side_effect=erro
        ), self.assertLogs(modulo.__name__, level="ERROR") as logs:
            with self.assertRaisesRegex(
                modulo.AnaliseIAError, "credencial da IA foi recusada"
            ):
                modulo.analisar_desvio(
                    {"descricao": "Farol do equipamento queimado."}
                )

        registro = " ".join(logs.output)
        self.assertIn("status=401", registro)
        self.assertIn("codigo=invalid_api_key", registro)
        self.assertIn("request_id=req-teste", registro)
        self.assertNotIn("segredo-teste", registro)

    def test_groq_request_identifies_client_and_distinguishes_http_403(self):
        caminho = ROOT / "app" / "services" / "groq_desvios.py"
        spec = importlib.util.spec_from_file_location("groq_desvios_headers_teste", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)

        def bloquear(requisicao, timeout):
            self.assertEqual(requisicao.get_header("Accept"), "application/json")
            self.assertEqual(
                requisicao.get_header("User-agent"),
                "TrackPlan/1.0 (Groq API client)",
            )
            payload = json.loads(requisicao.data.decode("utf-8"))
            schema = payload["response_format"]["json_schema"]["schema"]
            self.assertEqual(
                set(schema["properties"]),
                {"estado", "redacao_sugerida", "perguntas"},
            )
            self.assertEqual(schema["properties"]["perguntas"]["maxItems"], 3)
            self.assertEqual(timeout, 20)
            raise HTTPError(requisicao.full_url, 403, "Forbidden", {}, BytesIO(b""))

        with patch.dict("os.environ", {"GROQ_API_KEY": "segredo-teste"}), patch.object(
            modulo, "urlopen", side_effect=bloquear
        ), self.assertLogs(modulo.__name__, level="ERROR"):
            with self.assertRaisesRegex(
                modulo.AnaliseIAError, "bloqueada antes de chegar ao modelo"
            ):
                modulo.analisar_desvio(
                    {"descricao": "Farol do equipamento queimado."}
                )

    def test_groq_retries_without_response_format_when_strict_generation_fails(self):
        caminho = ROOT / "app" / "services" / "groq_desvios.py"
        spec = importlib.util.spec_from_file_location("groq_desvios_fallback_teste", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)

        erro = HTTPError(
            modulo.GROQ_URL,
            400,
            "Bad Request",
            {},
            BytesIO(b'{"error":{"code":"json_validate_failed","message":"invalid"}}'),
        )
        resultado_ia = {
            "estado": "concluida",
            "redacao_sugerida": "Farol dianteiro inoperante durante atividade noturna.",
            "perguntas": [],
        }
        resposta = BytesIO(
            json.dumps(
                {
                    "model": modulo.DEFAULT_MODEL,
                    "choices": [
                        {
                            "message": {
                                "content": "Resultado da análise:\n```json\n"
                                + json.dumps(resultado_ia)
                                + "\n```"
                            }
                        }
                    ],
                }
            ).encode("utf-8")
        )
        requisicoes = []

        def responder(requisicao, timeout):
            requisicoes.append(json.loads(requisicao.data.decode("utf-8")))
            if len(requisicoes) == 1:
                raise erro
            return resposta

        with patch.dict("os.environ", {"GROQ_API_KEY": "segredo-teste"}), patch.object(
            modulo, "urlopen", side_effect=responder
        ), self.assertLogs(modulo.__name__, level="WARNING"):
            resultado = modulo.analisar_desvio(
                {"descricao": "Farol do equipamento queimado."}
            )

        self.assertEqual(
            resultado["redacao_sugerida"],
            "Farol dianteiro inoperante durante atividade noturna.",
        )
        self.assertEqual(len(requisicoes), 2)
        self.assertEqual(requisicoes[0]["response_format"]["type"], "json_schema")
        self.assertNotIn("response_format", requisicoes[1])
        self.assertIn("sem markdown", requisicoes[1]["messages"][-1]["content"])

    def test_buffer_only_contains_records_without_action(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("d.status = 'aguardando_direcionamento'", source)
        self.assertIn("d.acao_id IS NULL", source)
        self.assertIn("INSERT INTO acoes", source)
        self.assertIn("status = 'em_tratamento'", source)

    def test_listing_has_requested_columns_and_logical_delete(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "app" / "templates" / "desvios.html").read_text(
            encoding="utf-8"
        )
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")
        for coluna in ("ID", "Data", "Relator", "Classificação", "Categoria", "Descrição"):
            self.assertIn(coluna, template)
        self.assertIn('id="relatorFiltroBusca"', template)
        self.assertIn('id="listaRelatoresFiltro"', template)
        self.assertIn("• Inativo", template)
        self.assertIn("list-group-item-action text-start", template)
        self.assertNotIn("<datalist", template)
        formulario = (
            ROOT / "app" / "templates" / "novo_desvio.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="listaRelatores"', formulario)
        self.assertIn('id="relatores-data"', formulario)
        self.assertNotIn("<datalist", formulario)
        self.assertIn("main.editar_desvio", template)
        self.assertIn("main.excluir_desvio", template)
        self.assertNotIn("Buffer de desvios</a></div>", template)
        self.assertIn("SET excluido_em = NOW(), excluido_por = %s", source)
        self.assertIn("SELECT id, nome, matricula, ativo FROM usuarios", source)
        self.assertIn("session.get('pode_direcionar_desvios') or is_admin", sidebar)

    def test_migration_contains_permissions_and_audit(self):
        migration = (ROOT / "docs" / "criar_modulo_desvios.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("acesso_desvios", migration)
        self.assertIn("pode_direcionar_desvios", migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS desvios_historico", migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS desvios_anexos", migration)


if __name__ == "__main__":
    unittest.main()

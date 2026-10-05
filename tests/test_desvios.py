import unittest
import importlib.util
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

    def test_buffer_only_contains_records_without_action(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("d.status = 'aguardando_direcionamento'", source)
        self.assertIn("d.acao_id IS NULL", source)
        self.assertIn("INSERT INTO acoes", source)
        self.assertIn("status = 'em_tratamento'", source)

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

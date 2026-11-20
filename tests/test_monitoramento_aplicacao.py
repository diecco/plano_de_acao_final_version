import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MonitoramentoAplicacaoTests(unittest.TestCase):
    def test_schema_has_sessions_errors_and_login_attempts(self):
        migration = (
            ROOT / "docs" / "criar_monitoramento_aplicacao.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS aplicacao_sessoes", migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS aplicacao_erros", migration)
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS aplicacao_tentativas_login", migration
        )
        self.assertNotIn("senha", migration.lower())

    def test_monitoring_page_is_admin_only_and_avoids_query_strings(self):
        view = (
            ROOT / "app" / "views" / "monitoramento_aplicacao.py"
        ).read_text(encoding="utf-8")
        service = (
            ROOT / "app" / "services" / "monitoramento_aplicacao.py"
        ).read_text(encoding="utf-8")
        self.assertIn("@admin_required", view)
        self.assertIn("request.path[:255]", service)
        self.assertNotIn("request.query_string", service)
        self.assertNotIn("request.form", service)
        self.assertIn("INTERVALO_ATIVIDADE_SEGUNDOS = 45", service)
        self.assertEqual(service.count("@app.after_request"), 1)
        after_request = service.split("@app.after_request", 1)[1]
        self.assertNotIn("UPDATE aplicacao_sessoes", after_request)

    def test_layout_has_authenticated_heartbeat(self):
        layout = (ROOT / "app" / "templates" / "layout.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("main.monitoramento_ping", layout)
        self.assertIn("document.visibilityState", layout)
        self.assertIn("session.get('usuario_id')", layout)

    def test_dashboard_uses_brasilia_and_standard_filter_actions(self):
        view = (
            ROOT / "app" / "views" / "monitoramento_aplicacao.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "monitoramento_aplicacao.html"
        ).read_text(encoding="utf-8")
        service = (
            ROOT / "app" / "services" / "monitoramento_aplicacao.py"
        ).read_text(encoding="utf-8")
        self.assertIn('ZoneInfo("America/Sao_Paulo")', view)
        self.assertIn("UTC_TIMESTAMP()", service)
        self.assertIn("Filtrar</button>", template)
        self.assertIn("Atualizar</a>", template)
        self.assertNotIn("Acessos, sessões, disponibilidade", template)

    def test_sidebar_exposes_monitoring_only_inside_admin_block(self):
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")
        admin_block = sidebar.split("{% if is_admin %}", 1)[1]
        self.assertIn("main.monitoramento_aplicacao", admin_block)
        self.assertIn(">Monitoramento<", admin_block)


if __name__ == "__main__":
    unittest.main()

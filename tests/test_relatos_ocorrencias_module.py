import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RelatosOcorrenciasModuleTest(unittest.TestCase):
    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for template in (
            "relatos_ocorrencias.html",
            "importar_relatos_ocorrencias.html",
            "detalhe_relato_ocorrencia.html",
        ):
            app.jinja_env.get_template(template)

    def test_module_uses_ssma_permission_and_cost_center_scope(self):
        source = (ROOT / "app" / "views" / "relatos_ocorrencias.py").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(source.count('@module_required("acesso_ssma")'), 3)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('{"administrador", "avancado"}', source)
        self.assertIn('session.get("gestor_ssma")', source)

    def test_sidebar_exposes_read_only_module(self):
        sidebar = (ROOT / "app" / "templates" / "components" / "sidebar.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("main.relatos_ocorrencias", sidebar)
        self.assertIn("Relatos de Ocorrências", sidebar)

    def test_listing_prioritizes_occurrence_description(self):
        template = (ROOT / "app" / "templates" / "relatos_ocorrencias.html").read_text(
            encoding="utf-8"
        )
        headers = [
            "<th>Solicitação", "<th>Data", "<th>Tipo",
            "<th>Descrição da ocorrência", "<th>Classificação",
            "<th>Condição/Comportamento", "<th>Situação",
            '<th class="text-center">Detalhes',
        ]
        positions = [template.index(header) for header in headers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("<th>Local", template)
        self.assertNotIn("<th>Requisitante", template)

    def test_migration_keeps_import_and_classification_separate(self):
        migration = (ROOT / "docs" / "criar_importacao_relatos_ocorrencias.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("relatos_ocorrencias_importacoes", migration)
        self.assertIn("relatos_ocorrencias_envolvidos", migration)
        self.assertIn("relatos_ocorrencias_importacao_erros", migration)
        self.assertNotIn("potencial_severidade", migration)


if __name__ == "__main__":
    unittest.main()

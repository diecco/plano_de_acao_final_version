import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ObservacaoComportamentalTests(unittest.TestCase):
    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for template in (
            "observacoes_comportamentais.html",
            "form_observacao_comportamental.html",
            "detalhe_observacao_comportamental.html",
        ):
            app.jinja_env.get_template(template)

    def test_module_has_exclusive_permission_and_cost_center_scope(self):
        source = (ROOT / "app" / "views" / "observacao_comportamental.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('@module_required("acesso_observacao_comportamental")', source)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('session.get("perfil") == "administrador"', source)

    def test_form_uses_markings_instead_of_deviation_total(self):
        template = (
            ROOT / "app" / "templates" / "form_observacao_comportamental.html"
        ).read_text(encoding="utf-8")
        listing = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Comportamentos observados", template)
        self.assertIn("Marcações", listing)
        self.assertNotIn("Total de desvios", template + listing)

    def test_schema_contains_original_six_categories_and_history(self):
        migration = (
            ROOT / "docs" / "criar_modulo_observacao_comportamental.sql"
        ).read_text(encoding="utf-8")
        for category in (
            "Reação das pessoas",
            "Posição das pessoas",
            "Parte do corpo exposta",
            "Ferramentas e equipamentos",
            "Procedimentos",
            "Ordem, limpeza e organização",
        ):
            self.assertIn(category, migration)
        self.assertIn("CREATE TABLE oc_historico", migration)
        self.assertIn("acesso_observacao_comportamental", migration)


if __name__ == "__main__":
    unittest.main()

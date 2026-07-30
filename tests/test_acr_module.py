import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AcrModuleStructureTests(unittest.TestCase):
    def test_acr_templates_compile(self):
        from app import create_app

        app = create_app()
        for template in (
            "investigacoes_causa_raiz.html",
            "nova_investigacao_causa_raiz.html",
        ):
            app.jinja_env.get_template(template)

    def test_routes_are_registered(self):
        routes = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
        self.assertIn("register_investigacao_causa_raiz_routes", routes)

    def test_acr_routes_require_module_permission(self):
        view = (
            ROOT / "app" / "views" / "investigacao_causa_raiz.py"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(
            view.count('@module_required("acesso_acr")'),
            2,
        )
        self.assertIn("acr_participantes", view)
        self.assertIn("centro_custos_id", view)

    def test_permission_is_available_in_user_flows(self):
        view = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("acesso_acr = %s", view)
        for template in (
            "usuarios.html",
            "editar_usuario.html",
            "permissoes_usuario.html",
        ):
            content = (ROOT / "app" / "templates" / template).read_text(
                encoding="utf-8"
            )
            self.assertIn('name="acesso_acr"', content)

    def test_migration_contains_required_foundation(self):
        migration = (ROOT / "docs" / "criar_modulo_acr.sql").read_text(
            encoding="utf-8"
        )
        for table in (
            "acr_investigacoes",
            "acr_5_porques",
            "acr_causas",
            "acr_acoes",
            "acr_verificacoes_eficacia",
            "acr_evidencias",
            "acr_historico",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", migration)
        self.assertIn("ACR", migration)


if __name__ == "__main__":
    unittest.main()

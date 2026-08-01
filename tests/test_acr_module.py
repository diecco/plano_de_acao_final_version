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
            "investigacao_causa_raiz_detalhe.html",
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
            5,
        )
        self.assertIn("acr_participantes", view)
        self.assertIn("centro_custos_id", view)

    def test_new_acr_inherits_logged_user_cost_center(self):
        view = (
            ROOT / "app" / "views" / "investigacao_causa_raiz.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "nova_investigacao_causa_raiz.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'centro_custos_id = session.get("centro_custos_id")',
            view,
        )
        self.assertNotIn('name="centro_custos_id"', template)
        self.assertIn("btn btn-cinza", template)
        self.assertIn("btn btn-laranja", template)

    def test_acr_listing_has_safe_sorting_and_date_filters(self):
        view = (
            ROOT / "app" / "views" / "investigacao_causa_raiz.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "investigacoes_causa_raiz.html"
        ).read_text(encoding="utf-8")
        self.assertIn("ORDENACOES_ACR", view)
        self.assertIn("if ordenacao not in ORDENACOES_ACR", view)
        self.assertIn("i.data_ocorrencia >= %s", view)
        self.assertIn("i.data_ocorrencia <= %s", view)
        self.assertIn('name="data_inicio"', template)
        self.assertIn('name="data_fim"', template)
        self.assertIn("cabecalho_ordenavel", template)
        self.assertIn("btn btn-laranja", template)
        self.assertIn("btn btn-cinza", template)

    def test_five_whys_workflow_has_server_side_rules(self):
        view = (
            ROOT / "app" / "views" / "investigacao_causa_raiz.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "investigacao_causa_raiz_detalhe.html"
        ).read_text(encoding="utf-8")
        self.assertIn("salvar_5_porques_acr", view)
        self.assertIn("Preencha os Porquês em sequência", view)
        self.assertIn("causa_raiz_ordem", view)
        self.assertIn("acr_causas", view)
        self.assertIn('name="causa_raiz_ordem"', template)
        self.assertEqual(
            template.count('name="pergunta_{{ item.ordem }}"'),
            1,
        )
        self.assertEqual(
            template.count('name="resposta_{{ item.ordem }}"'),
            1,
        )
        self.assertIn("Cada nível preenchido precisa ter pergunta e resposta", view)

    def test_acr_action_plan_links_existing_action_structure(self):
        view = (
            ROOT / "app" / "views" / "investigacao_causa_raiz.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "investigacao_causa_raiz_detalhe.html"
        ).read_text(encoding="utf-8")
        self.assertIn("def criar_acao_acr", view)
        self.assertIn("INSERT INTO acoes", view)
        self.assertIn("INSERT INTO acr_acoes", view)
        self.assertIn("Confirme a causa raiz", view)
        self.assertIn("main.criar_acao_acr", template)
        self.assertIn("Plano de ação", template)

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

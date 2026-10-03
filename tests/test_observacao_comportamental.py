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

    def test_listing_matches_hs_filter_sort_and_pagination_pattern(self):
        template = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertIn('list="listaObservadoresOc"', template)
        self.assertIn("Digite o nome ou a matrícula", template)
        self.assertIn("bi-caret-up-fill", template)
        self.assertIn("bi-caret-down-fill", template)
        self.assertIn('class="pagination pagination-sm mb-0"', template)
        self.assertNotIn('name="status"', template)
        self.assertNotIn(">Nova<", template)
        self.assertIn('request.args.get("observador_id", type=int)', source)
        self.assertIn('"marcacoes": "total_marcacoes"', source)

    def test_registration_form_uses_inherited_scope_and_guided_items(self):
        template = (
            ROOT / "app" / "templates" / "form_observacao_comportamental.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertIn("Registrar Observação Comportamental", template)
        self.assertIn("Centro de custos não vinculado", template)
        self.assertIn('name="setor_observado"', template)
        self.assertIn("{% for setor in setores %}", template)
        self.assertIn("item.ajuda", template)
        self.assertIn("position:absolute; right:3.5rem", template)
        self.assertIn("background-color:#f36c21", template)
        self.assertIn('class="btn btn-laranja" type="submit">Salvar</button>', template)
        self.assertNotIn("Salvar rascunho", template)
        self.assertNotIn("Concluir</button>", template)
        self.assertIn("EXPLICACOES_ITENS", source)
        self.assertIn("FROM setores", source)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('"status": "concluida"', source)

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
        self.assertIn("CREATE TABLE IF NOT EXISTS oc_historico", migration)
        self.assertIn("acesso_observacao_comportamental", migration)


if __name__ == "__main__":
    unittest.main()

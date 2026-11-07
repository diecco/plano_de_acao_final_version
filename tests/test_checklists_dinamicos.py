import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConfigurableChecklistSketchTests(unittest.TestCase):
    def test_migration_is_additive_and_scoped_by_cost_center(self):
        sql = (ROOT / "docs" / "criar_catalogo_checklists_dinamicos.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_modelos", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_modelos_centros", sql)
        self.assertIn("REFERENCES centros_custos(id)", sql)

    def test_sidebar_contains_dynamic_slots_and_administration_link(self):
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("checklists_sidebar_ssma", sidebar)
        self.assertIn("checklists_sidebar_gestao", sidebar)
        self.assertIn("main.checklists_dinamicos", sidebar)
        self.assertIn("main.abrir_checklist_dinamico", sidebar)

    def test_scope_query_accepts_global_or_selected_cost_center(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("cm.abrangencia = 'global'", source)
        self.assertIn("checklist_modelos_centros", source)
        self.assertIn("cm.status = 'publicado'", source)
        self.assertIn("cm.exibir_menu = 1", source)

    def test_sidebar_configuration_is_conditional_and_uses_orange_switch(self):
        template = (
            ROOT / "app" / "templates" / "checklists_dinamicos.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Primeiro esboço", template)
        self.assertIn('id="blocoSidebar" hidden', template)
        self.assertIn("atualizarSidebar", template)
        self.assertIn("background-color: #f26722", template)

    def test_verification_item_builder_has_server_side_validation(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def validar_estrutura", source)
        self.assertIn("O limite é de 200 itens por checklist", source)
        self.assertIn("negative_comment", source)
        self.assertIn("estrutura_json", source)

        javascript = (
            ROOT / "app" / "static" / "js" / "checklist-builder.js"
        ).read_text(encoding="utf-8")
        editor = (
            ROOT / "app" / "templates" / "checklist_dinamico_editar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Adicionar seção", editor)
        self.assertIn("Matriz de avaliação", javascript)
        self.assertIn("Exigir descrição do desvio", javascript)

    def test_items_migration_is_reexecutable(self):
        sql = (
            ROOT / "docs" / "adicionar_itens_checklists_dinamicos.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("information_schema.COLUMNS", sql)
        self.assertIn("ADD COLUMN estrutura_json JSON", sql)

    def test_server_accepts_a_valid_definition_and_rejects_empty_sections(self):
        from app.views.checklists_dinamicos import validar_estrutura

        valid = [{
            "title": "Condições do local",
            "questions": [{
                "text": "O local está sinalizado?",
                "type": "conformity",
                "required": True,
                "negative_comment": True,
                "negative_evidence": False,
                "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(valid))
        self.assertEqual(clean[0]["questions"][0]["text"], "O local está sinalizado?")

        invalid = [{"title": "Sem itens", "questions": []}]
        with self.assertRaisesRegex(ValueError, "ao menos um item"):
            validar_estrutura(json.dumps(invalid))


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

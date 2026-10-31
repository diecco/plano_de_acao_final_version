import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HorasSegurancaAuditadosTests(unittest.TestCase):
    def test_migracao_preserva_historico_e_cria_acompanhantes(self):
        sql = (ROOT / "docs" / "separar_auditados_participantes_hs.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS hs_registros_acompanhantes", sql)
        self.assertNotIn("UPDATE hs_registros_participantes", sql)
        self.assertNotIn("DELETE FROM hs_registros_participantes", sql)

    def test_formulario_separa_auditados_e_participantes(self):
        template = (ROOT / "app" / "templates" / "lancar_hs.html").read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(encoding="utf-8")
        self.assertIn('input.name = "auditados"', template)
        self.assertIn('id="seletorAuditados"', template)
        self.assertIn('id="seletorAcompanhantes"', template)
        self.assertIn('input.name = "participantes"', template)
        self.assertIn("hs-multiselect-opcao", template)
        self.assertIn("_sincronizar_acompanhantes_hs", view)
        self.assertIn('request.form.getlist("participantes")', view)


if __name__ == "__main__":
    unittest.main()


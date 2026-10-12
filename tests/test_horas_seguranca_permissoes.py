import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HorasSegurancaPermissoesTests(unittest.TestCase):
    def test_modulo_usa_politica_central_em_todos_os_caminhos(self):
        source = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "app" / "templates" / "listar_hs.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("filtro_escopo_visualizacao", source)
        self.assertIn("def _pode_visualizar_hs", source)
        self.assertIn("def _pode_alterar_hs", source)
        self.assertIn("def _pode_excluir_hs", source)
        self.assertIn("_pode_alterar_hs(registro)", source)
        self.assertIn("_pode_excluir_hs(registro)", source)
        self.assertNotIn("pode_acessar_ssma", source)
        self.assertIn("hs.pode_editar", template)
        self.assertIn("hs.pode_excluir", template)
        self.assertNotIn(
            "hs.id_auditor == session.get('usuario_id')",
            template,
        )

    def test_escopo_considera_centro_atual_do_autor(self):
        source = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'campo_centro="u.centro_custos_id"',
            source,
        )
        self.assertIn("centro_custos_autor_id", source)


if __name__ == "__main__":
    unittest.main()

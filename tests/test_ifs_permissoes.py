import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IfsPermissoesTests(unittest.TestCase):
    def test_listagem_e_operacoes_usam_politica_central(self):
        source = (ROOT / "app" / "views" / "ifs.py").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "app" / "templates" / "listar_ifs.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("filtro_escopo_visualizacao", source)
        self.assertIn("def _pode_alterar_ifs", source)
        self.assertIn("def _pode_excluir_ifs", source)
        self.assertNotIn("pode_acessar_ssma", source)
        self.assertIn("ifs.pode_editar", template)
        self.assertIn("ifs.pode_excluir", template)
        self.assertNotIn(
            "ifs.criado_por == session.get('usuario_id')",
            template,
        )

    def test_autoria_e_centro_possuem_finalidades_distintas(self):
        source = (ROOT / "app" / "views" / "ifs.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('registro.get("criado_por")', source)
        self.assertIn('registro.get("centro_custos_registro_id")', source)
        self.assertIn('campo_centro="u.centro_custos_id"', source)

    def test_edicao_preserva_profissional_e_centro_do_registro(self):
        source = (ROOT / "app" / "views" / "ifs.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "profissional_sesmt_id = inspecao['profissional_sesmt_id']",
            source,
        )
        self.assertIn(
            "centro_custo_id = inspecao['centro_custos_registro_id']",
            source,
        )


if __name__ == "__main__":
    unittest.main()

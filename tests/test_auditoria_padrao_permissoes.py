import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AuditoriaPadraoPermissoesTests(unittest.TestCase):
    def test_listagem_e_operacoes_usam_politica_central(self):
        source = (
            ROOT / "app" / "views" / "auditoria_padrao.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "app" / "templates" / "listar_ap.html"
        ).read_text(encoding="utf-8")

        self.assertIn("filtro_escopo_visualizacao", source)
        self.assertIn("def _pode_alterar_auditoria_padrao", source)
        self.assertIn("def _pode_excluir_auditoria_padrao", source)
        self.assertNotIn("pode_acessar_ssma", source)
        self.assertIn("ap.pode_editar", template)
        self.assertIn("ap.pode_excluir", template)
        self.assertNotIn(
            "ap.criado_por == session.get('usuario_id')",
            template,
        )

    def test_autoria_e_centro_possuem_finalidades_distintas(self):
        source = (
            ROOT / "app" / "views" / "auditoria_padrao.py"
        ).read_text(encoding="utf-8")

        self.assertIn('registro.get("criado_por")', source)
        self.assertIn('registro.get("centro_custos_registro_id")', source)
        self.assertIn(
            'campo_centro="auditado.centro_custos_id"',
            source,
        )


if __name__ == "__main__":
    unittest.main()

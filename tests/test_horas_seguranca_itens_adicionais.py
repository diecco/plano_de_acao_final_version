import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class HorasSegurancaItensAdicionaisTests(unittest.TestCase):
    def test_migracao_cria_observacoes_e_tabela_adicional(self):
        sql = (ROOT / "docs" / "adicionar_observacoes_itens_adicionais_hs.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("observacoes_gerais", sql)
        self.assertIn("CREATE TABLE hs_registros_adicionais", sql)
        self.assertIn("id_acao_gerada INT NULL", sql)

    def test_formulario_permite_multiplos_itens_e_acao_opcional(self):
        template = (ROOT / "app" / "templates" / "lancar_hs.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("adicionarItemAdicionalHS", template)
        self.assertIn('name="adicional_item[]"', template)
        self.assertIn('name="adicional_gerar_acao[]" value="0"', template)
        self.assertIn('name="observacoes_gerais"', template)

    def test_backend_nao_mistura_adicionais_com_respostas_do_checklist(self):
        view = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("INSERT INTO hs_registros_adicionais", view)
        self.assertIn('if adicional["gerar_acao"]:', view)
        self.assertIn('registro["itens_adicionais"]', view)

    def test_pdf_exibe_observacoes_e_itens_adicionais(self):
        pdf = (ROOT / "app" / "utils" / "hs_pdf.py").read_text(encoding="utf-8")
        self.assertIn("Observações gerais", pdf)
        self.assertIn("Outros itens identificados", pdf)
        self.assertIn("Sem ação gerada", pdf)


if __name__ == "__main__":
    unittest.main()

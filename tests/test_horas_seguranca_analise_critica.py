import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class HorasSegurancaAnaliseCriticaTests(unittest.TestCase):
    def setUp(self):
        self.view = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(
            encoding="utf-8"
        )
        self.template = (
            ROOT / "app" / "templates" / "analise_critica_hs.html"
        ).read_text(encoding="utf-8")

    def test_migracao_preserva_centro_e_normaliza_participantes(self):
        sql = (ROOT / "docs" / "normalizar_hs_analise_critica.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("ADD COLUMN centro_custos_id", sql)
        self.assertIn("CREATE TABLE hs_registros_participantes", sql)
        self.assertIn("INSERT IGNORE INTO hs_registros_participantes", sql)
        self.assertIn("JSON_TABLE", sql)

    def test_novos_registros_gravam_centro_e_participantes_normalizados(self):
        self.assertIn("_sincronizar_participantes_hs", self.view)
        self.assertIn("centro_custos_id,", self.view)
        self.assertIn("INSERT INTO hs_registros_participantes", self.view)

    def test_score_considera_nc_e_desvios_adicionais(self):
        self.assertIn("int(registro['total_c']) + int(registro['total_nc'])", self.view)
        self.assertIn("int(registro['desvios_adicionais'])", self.view)
        self.assertIn("registro['score']", self.view)

    def test_relatorio_oferece_filtros_e_indicadores_macro(self):
        for campo in (
            'name="data_inicio"', 'name="data_fim"',
            'name="participante_id"', 'name="auditor_id"',
            'name="tema_id"', 'name="score_minimo"',
            'name="score_maximo"', 'name="centro_custos_id"',
        ):
            self.assertIn(campo, self.template)
        self.assertIn("Score médio", self.template)
        self.assertIn("Pessoas alcançadas", self.template)
        self.assertIn("Análise por tema", self.template)
        self.assertIn("Análise por auditor", self.template)
        self.assertIn("Desvios recorrentes", self.template)


if __name__ == "__main__":
    unittest.main()

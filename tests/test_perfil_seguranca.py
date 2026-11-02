import unittest
from datetime import date
from pathlib import Path

from app.views.perfil_seguranca import _periodo_perfil


class PerfilSegurancaTests(unittest.TestCase):
    def test_periodo_resolve_mes_inteiro(self):
        mes, inicio, fim = _periodo_perfil("2024-02", date(2026, 10, 31))
        self.assertEqual("2024-02", mes)
        self.assertEqual(date(2024, 2, 1), inicio)
        self.assertEqual(date(2024, 2, 29), fim)

    def test_periodo_invalido_retorna_mes_atual(self):
        mes, inicio, fim = _periodo_perfil("invalido", date(2026, 10, 31))
        self.assertEqual("2026-10", mes)
        self.assertEqual(date(2026, 10, 1), inicio)
        self.assertEqual(date(2026, 10, 31), fim)

    def test_consulta_usa_nome_real_da_tabela_de_auditorias(self):
        fonte = (
            Path(__file__).parents[1] / "app" / "views" / "perfil_seguranca.py"
        ).read_text(encoding="utf-8")
        self.assertIn("FROM auditorias_padrao ap", fonte)
        self.assertNotIn("FROM auditoria_padrao ap", fonte)

    def test_horas_de_seguranca_consideram_relacao_e_campo_legado(self):
        fonte = (
            Path(__file__).parents[1] / "app" / "views" / "perfil_seguranca.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LEFT JOIN hs_registros_participantes hp", fonte)
        self.assertIn("FIND_IN_SET", fonte)
        self.assertIn("COUNT(DISTINCT r.id)", fonte)


if __name__ == "__main__":
    unittest.main()


import unittest
from datetime import date

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


if __name__ == "__main__":
    unittest.main()


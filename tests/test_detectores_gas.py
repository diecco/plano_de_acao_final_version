import unittest
from datetime import date

from app.views.detectores_gas import (
    converter_data_opcional,
    normalizar_patrimonio,
    patrimonio_valido,
)


class DetectoresGasTests(unittest.TestCase):
    def test_normaliza_patrimonio(self):
        self.assertEqual(normalizar_patrimonio(" ptdg-1921 "), "PTDG-1921")

    def test_aceita_patrimonio_no_padrao_definido(self):
        self.assertTrue(patrimonio_valido("PTDG-1921"))
        self.assertTrue(patrimonio_valido("ptdg-1921"))

    def test_rejeita_patrimonio_fora_do_padrao(self):
        invalidos = (
            "PTD-1921",
            "PTDGG-1921",
            "PTDG1921",
            "PTDG-921",
            "1921-PTDG",
            "PT1G-1921",
        )
        for patrimonio in invalidos:
            with self.subTest(patrimonio=patrimonio):
                self.assertFalse(patrimonio_valido(patrimonio))

    def test_converte_data_opcional(self):
        self.assertIsNone(converter_data_opcional(""))
        self.assertEqual(
            converter_data_opcional("2026-07-23"),
            date(2026, 7, 23),
        )

    def test_rejeita_data_invalida(self):
        with self.assertRaises(ValueError):
            converter_data_opcional("23/07/2026")


if __name__ == "__main__":
    unittest.main()

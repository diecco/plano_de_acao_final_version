import unittest
from datetime import date
from pathlib import Path

from app.views.detectores_gas import (
    STATUS_DASHBOARD,
    converter_data_opcional,
    normalizar_patrimonio,
    normalizar_rfid,
    patrimonio_valido,
)

ROOT = Path(__file__).resolve().parents[1]
VIEW_SOURCE = (
    ROOT / "app" / "views" / "detectores_gas.py"
).read_text(encoding="utf-8")
DASHBOARD_TEMPLATE = (
    ROOT / "app" / "templates" / "painel_detectores_gas.html"
).read_text(encoding="utf-8")


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

    def test_normaliza_rfid_sem_alterar_o_codigo(self):
        self.assertEqual(normalizar_rfid(" 0012345678\n"), "0012345678")

    def test_dashboard_contem_todos_os_status_operacionais(self):
        self.assertEqual(
            set(STATUS_DASHBOARD),
            {"disponivel", "em_uso", "em_calibracao", "com_defeito"},
        )

    def test_dashboard_exibe_somente_detectores_ativos(self):
        self.assertIn('condicoes = ["d.ativo = 1"]', VIEW_SOURCE)

    def test_dashboard_ordena_pelo_numero_do_patrimonio(self):
        self.assertIn(
            "CAST(RIGHT(d.patrimonio, 4) AS UNSIGNED)",
            VIEW_SOURCE,
        )

    def test_dashboard_prepara_fluxos_de_entrega_e_devolucao(self):
        self.assertIn('"acao": "Iniciar entrega"', VIEW_SOURCE)
        self.assertIn('"acao": "Registrar devolução"', VIEW_SOURCE)
        self.assertIn("validação RFID", DASHBOARD_TEMPLATE)

    def test_devolucao_exige_o_mesmo_usuario_da_retirada(self):
        self.assertIn(
            'devolvente["id"] != movimentacao["retirado_por_id"]',
            VIEW_SOURCE,
        )

    def test_modal_devolucao_exibe_usuario_em_posse(self):
        self.assertIn("Em posse de", DASHBOARD_TEMPLATE)
        self.assertIn("modalPosseDetector", DASHBOARD_TEMPLATE)
        self.assertIn("card.dataset.usuarioPosse", DASHBOARD_TEMPLATE)

    def test_modal_nao_exibe_centro_e_destaca_rfid_em_laranja(self):
        self.assertNotIn("modalCentroDetector", DASHBOARD_TEMPLATE)
        self.assertIn("rfid-identificado", DASHBOARD_TEMPLATE)
        self.assertIn("color: #ea6a23", DASHBOARD_TEMPLATE)

    def test_responsavel_rfid_deve_ser_o_usuario_logado(self):
        self.assertGreaterEqual(
            VIEW_SOURCE.count(
                'responsavel["id"] != session.get("usuario_id")'
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()

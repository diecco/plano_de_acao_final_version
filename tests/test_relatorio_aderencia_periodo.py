import unittest
from datetime import date

from app.views.agenda_ssma import _resolver_periodo_aderencia


class RelatorioAderenciaPeriodoTest(unittest.TestCase):
    def test_resolve_mes_atual_anterior_e_proximo(self):
        hoje = date(2026, 1, 15)

        atual = _resolver_periodo_aderencia('mes_atual', hoje=hoje)
        anterior = _resolver_periodo_aderencia('mes_anterior', hoje=hoje)
        proximo = _resolver_periodo_aderencia('mes_proximo', hoje=hoje)

        self.assertEqual(atual, (date(2026, 1, 1), date(2026, 1, 31), '2026-01'))
        self.assertEqual(anterior, (date(2025, 12, 1), date(2025, 12, 31), '2025-12'))
        self.assertEqual(proximo, (date(2026, 2, 1), date(2026, 2, 28), '2026-02'))

    def test_resolve_mes_e_ano_escolhidos(self):
        resultado = _resolver_periodo_aderencia(
            'mes_ano',
            mes_referencia='2028-02'
        )

        self.assertEqual(
            resultado,
            (date(2028, 2, 1), date(2028, 2, 29), '2028-02')
        )

    def test_aceita_intervalo_personalizado_no_mesmo_mes(self):
        resultado = _resolver_periodo_aderencia(
            'personalizado',
            data_inicio='2026-10-07',
            data_fim='2026-10-21'
        )

        self.assertEqual(
            resultado,
            (date(2026, 10, 7), date(2026, 10, 21), '2026-10')
        )

    def test_rejeita_intervalo_entre_meses(self):
        with self.assertRaisesRegex(ValueError, 'mesmo mês'):
            _resolver_periodo_aderencia(
                'personalizado',
                data_inicio='2026-10-31',
                data_fim='2026-11-01'
            )

    def test_rejeita_datas_invertidas(self):
        with self.assertRaisesRegex(ValueError, 'posterior'):
            _resolver_periodo_aderencia(
                'personalizado',
                data_inicio='2026-10-20',
                data_fim='2026-10-10'
            )


if __name__ == '__main__':
    unittest.main()


import unittest

from app.views.melhorias import _escopo_visualizacao_melhorias


class EscopoVisualizacaoMelhoriasTests(unittest.TestCase):
    def test_basico_visualiza_centro_de_custos(self):
        filtro, valores = _escopo_visualizacao_melhorias("basico", 7)
        self.assertEqual(filtro, "m.centro_custo_id = %s")
        self.assertEqual(valores, [7])

    def test_intermediario_visualiza_centro_de_custos(self):
        filtro, valores = _escopo_visualizacao_melhorias("intermediario", 9)
        self.assertEqual(filtro, "m.centro_custo_id = %s")
        self.assertEqual(valores, [9])

    def test_avancado_e_administrador_mantem_escopo_global(self):
        for perfil in ("avancado", "administrador"):
            with self.subTest(perfil=perfil):
                self.assertEqual(
                    _escopo_visualizacao_melhorias(perfil, 3),
                    (None, []),
                )

    def test_usuario_sem_centro_nao_recebe_dados(self):
        self.assertEqual(
            _escopo_visualizacao_melhorias("basico", None),
            ("1 = 0", []),
        )


if __name__ == "__main__":
    unittest.main()

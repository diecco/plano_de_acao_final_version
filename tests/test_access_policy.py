import unittest

from app.access_policy import (
    filtro_escopo_visualizacao,
    pode_alterar_registro,
    pode_excluir_registro,
    pode_visualizar_registro,
)


class AccessPolicyTests(unittest.TestCase):
    def test_basico_visualiza_centro_e_altera_apenas_proprios(self):
        self.assertTrue(pode_visualizar_registro("basico", 10, 10))
        self.assertFalse(pode_visualizar_registro("basico", 10, 20))
        self.assertTrue(pode_alterar_registro("basico", 7, 10, 7, 10))
        self.assertFalse(pode_alterar_registro("basico", 7, 10, 8, 10))

    def test_intermediario_visualiza_e_altera_o_proprio_centro(self):
        self.assertTrue(pode_visualizar_registro("intermediario", 10, 10))
        self.assertTrue(pode_alterar_registro("intermediario", 7, 10, 8, 10))
        self.assertFalse(pode_alterar_registro("intermediario", 7, 10, 8, 20))

    def test_avancado_e_administrador_possuem_escopo_global(self):
        for perfil in ("avancado", "administrador"):
            self.assertTrue(pode_visualizar_registro(perfil, 10, 20))
            self.assertTrue(pode_alterar_registro(perfil, 7, 10, 8, 20))
            self.assertTrue(pode_excluir_registro(perfil, 7, 10, 8, 20))
            self.assertEqual(filtro_escopo_visualizacao(perfil, 10, "d"), ("1 = 1", []))

    def test_filtro_de_visualizacao_restringe_perfis_locais(self):
        self.assertEqual(
            filtro_escopo_visualizacao("basico", 10, "d"),
            ("d.centro_custos_id = %s", [10]),
        )
        self.assertEqual(
            filtro_escopo_visualizacao("intermediario", None, "d"),
            ("1 = 0", []),
        )


if __name__ == "__main__":
    unittest.main()

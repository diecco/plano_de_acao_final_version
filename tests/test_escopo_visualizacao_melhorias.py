import pathlib
import unittest

from app.views.melhorias import _escopo_visualizacao_melhorias


ROOT = pathlib.Path(__file__).resolve().parents[1]


class EscopoVisualizacaoMelhoriasTests(unittest.TestCase):
    def test_basico_visualiza_centro_de_custos(self):
        filtro, valores = _escopo_visualizacao_melhorias("basico", 7)
        self.assertEqual(filtro, "m.centro_custo_id = %s")
        self.assertEqual(valores, [7])

    def test_intermediario_visualiza_centro_de_custos(self):
        filtro, valores = _escopo_visualizacao_melhorias("intermediario", 9)
        self.assertEqual(filtro, "m.centro_custo_id = %s")
        self.assertEqual(valores, [9])

    def test_avancado_tambem_visualiza_somente_o_centro(self):
        self.assertEqual(
            _escopo_visualizacao_melhorias("avancado", 3),
            ("m.centro_custo_id = %s", [3]),
        )

    def test_administrador_mantem_escopo_global(self):
        self.assertEqual(
            _escopo_visualizacao_melhorias("administrador", 3),
            (None, []),
        )

    def test_template_exibe_acoes_para_criador_ou_administrador(self):
        template = (
            ROOT / "app" / "templates" / "listar_melhoria.html"
        ).read_text(encoding="utf-8")
        self.assertIn("m.criado_por == session.get('usuario_id')", template)
        self.assertIn("session.get('perfil') == 'administrador'", template)

    def test_usuario_sem_centro_nao_recebe_dados(self):
        self.assertEqual(
            _escopo_visualizacao_melhorias("basico", None),
            ("1 = 0", []),
        )


if __name__ == "__main__":
    unittest.main()

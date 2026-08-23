import pathlib
import unittest

from app.views.melhorias import _pode_visualizar_melhoria


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VisualizacaoMelhoriaTests(unittest.TestCase):
    def test_usuario_do_mesmo_centro_pode_visualizar(self):
        self.assertTrue(_pode_visualizar_melhoria("intermediario", 1, 1))

    def test_usuario_de_outro_centro_nao_pode_visualizar(self):
        self.assertFalse(_pode_visualizar_melhoria("intermediario", 1, 2))

    def test_administrador_pode_visualizar_qualquer_centro(self):
        self.assertTrue(_pode_visualizar_melhoria("administrador", None, 2))

    def test_template_mantem_visualizacao_para_todos(self):
        template = (
            ROOT / "app" / "templates" / "listar_melhoria.html"
        ).read_text(encoding="utf-8")
        self.assertIn("main.visualizar_melhoria", template)
        self.assertIn("bi bi-eye", template)


if __name__ == "__main__":
    unittest.main()

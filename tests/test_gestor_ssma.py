import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GestorSsmaTests(unittest.TestCase):
    def test_desvios_e_observacao_usam_acesso_ssma(self):
        desvios = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        observacao = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn('module_required("acesso_desvios")', desvios)
        self.assertNotIn(
            'module_required("acesso_observacao_comportamental")',
            observacao,
        )
        self.assertIn('module_required("acesso_ssma")', desvios)
        self.assertIn('module_required("acesso_ssma")', observacao)

    def test_buffer_exige_gestor_ssma(self):
        source = (ROOT / "app" / "views" / "desvios.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "@tratar_buffer_desvios_required\n    def buffer_desvios",
            source,
        )
        self.assertIn(
            "@tratar_buffer_desvios_required\n    def direcionar_desvio",
            source,
        )

    def test_persona_e_migracao_estao_conectadas(self):
        autenticacao = (
            ROOT / "app" / "views" / "autenticacao.py"
        ).read_text(encoding="utf-8")
        usuarios = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )
        migration = (ROOT / "docs" / "criar_gestor_ssma.sql").read_text(
            encoding="utf-8"
        )

        self.assertIn("session['gestor_ssma']", autenticacao)
        self.assertIn("gestor_ssma = %s", usuarios)
        self.assertIn("ADD COLUMN gestor_ssma", migration)


if __name__ == "__main__":
    unittest.main()

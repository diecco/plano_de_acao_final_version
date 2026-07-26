import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PermissaoDetectoresUsuariosTests(unittest.TestCase):
    def setUp(self):
        self.usuarios_view = (
            ROOT / "app" / "views" / "usuarios.py"
        ).read_text(encoding="utf-8")
        self.auth_view = (
            ROOT / "app" / "views" / "autenticacao.py"
        ).read_text(encoding="utf-8")
        self.detectores_view = (
            ROOT / "app" / "views" / "detectores_gas.py"
        ).read_text(encoding="utf-8")
        self.sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")

    def test_cadastro_e_edicao_persistem_nova_permissao(self):
        self.assertGreaterEqual(
            self.usuarios_view.count("acesso_detectores_gas"),
            12,
        )

    def test_login_carrega_permissao_na_sessao(self):
        self.assertIn(
            "session['acesso_detectores_gas']",
            self.auth_view,
        )

    def test_rotas_web_e_api_exigem_permissao_do_modulo(self):
        self.assertIn(
            '@module_required("acesso_detectores_gas")',
            self.detectores_view,
        )
        self.assertIn(
            '@api_module_required("acesso_detectores_gas")',
            self.detectores_view,
        )
        self.assertNotIn("@admin_required", self.detectores_view)

    def test_sidebar_respeita_permissao_e_admin(self):
        self.assertIn(
            "session.get('acesso_detectores_gas') or is_admin",
            self.sidebar,
        )

    def test_campos_sensiveis_desabilitam_sugestoes(self):
        for template_name in ("usuarios.html", "editar_usuario.html"):
            source = (
                ROOT / "app" / "templates" / template_name
            ).read_text(encoding="utf-8")
            self.assertIn('name="acesso_detectores_gas"', source)
            self.assertIn('autocomplete="new-password"', source)
            self.assertIn('data-lpignore="true"', source)
            self.assertRegex(
                source,
                r'id="uid_rfid"[\s\S]{0,300}autocomplete="off"',
            )


if __name__ == "__main__":
    unittest.main()

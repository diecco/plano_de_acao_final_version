import re
import unittest
from pathlib import Path

from flask import render_template, session

from app import create_app


ROOT = Path(__file__).resolve().parents[1]
SIDEBAR_TEMPLATE = ROOT / "app" / "templates" / "components" / "sidebar.html"


class LayoutNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def render_layout(self, path, perfil=None):
        with self.app.test_request_context(path):
            if perfil:
                session["perfil"] = perfil
                session["nome"] = "Usuário de teste"
            return render_template("layout.html")

    def test_layout_autenticado_renderiza_navegacao(self):
        html = self.render_layout("/dashboard", perfil="administrador")

        self.assertIn('id="appSidebar"', html)
        self.assertIn("app-topbar", html)
        self.assertIn("Planos de Ação", html)
        self.assertIn("Detectores de Gás", html)
        self.assertIn("Administração", html)

    def test_login_nao_renderiza_navegacao_interna(self):
        html = self.render_layout("/login")

        self.assertNotIn('id="appSidebar"', html)
        self.assertNotIn("app-topbar", html)
        self.assertIn("main-content-login", html)

    def test_todos_os_endpoints_da_sidebar_existem(self):
        source = SIDEBAR_TEMPLATE.read_text(encoding="utf-8")
        referenced = set(re.findall(r"url_for\(['\"]([^'\"]+)", source))
        available = {rule.endpoint for rule in self.app.url_map.iter_rules()}

        self.assertEqual(set(), referenced - available)

    def test_sidebar_nao_duplica_links_em_flyouts(self):
        source = SIDEBAR_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("sidebar-flyout", source)
        self.assertIn('data-bs-parent="#sidebarMenuAccordion"', source)
        self.assertIn('id="sidebarSearch"', source)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InicioComunicadosTests(unittest.TestCase):
    def test_inicio_and_admin_templates_compile(self):
        from app import create_app

        app = create_app()
        app.jinja_env.get_template("inicio.html")
        app.jinja_env.get_template("comunicados_visuais.html")

    def test_home_is_independent_from_module_permissions(self):
        source = (ROOT / "app" / "views" / "inicio.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('@blueprint.route("/inicio")', source)
        self.assertNotIn('@module_required', source)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn("cv.corporativo = 1", source)
        self.assertIn("comunicados_visuais_centros", source)
        self.assertIn("UploadService.existe", source)

    def test_visual_carousel_is_image_only_and_dismissible(self):
        template = (ROOT / "app" / "templates" / "inicio.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("fundo_gestao_rotina.png", template)
        self.assertIn('class="btn-close"', template)
        self.assertIn('data-bs-dismiss="modal"', template)
        self.assertIn('class="carousel slide"', template)
        self.assertIn("comunicados/' ~ comunicado.imagem", template)
        self.assertIn(
            "calc(100dvh - var(--topbar-height) - 56px)",
            template,
        )

    def test_visual_communications_use_persistent_uploads(self):
        upload_source = (ROOT / "app" / "upload_security.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"comunicados"', upload_source)

    def test_admin_can_replace_a_visual_communication_image(self):
        source = (ROOT / "app" / "views" / "inicio.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "comunicados_visuais.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '"/admin/comunicados/<int:comunicado_id>/imagem"',
            source,
        )
        self.assertIn("substituir_imagem_comunicado_visual", template)
        self.assertIn("Editar imagem", template)

    def test_login_and_permission_denials_return_to_home(self):
        authentication = (
            ROOT / "app" / "views" / "autenticacao.py"
        ).read_text(encoding="utf-8")
        decorators = (ROOT / "app" / "decorators.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("return redirect('/inicio')", authentication)
        self.assertIn("url_for('main.inicio')", decorators)

    def test_schema_supports_corporate_and_cost_center_messages(self):
        migration = (
            ROOT / "docs" / "criar_comunicados_visuais.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS comunicados_visuais", migration)
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS comunicados_visuais_centros",
            migration,
        )
        self.assertIn("centro_custos_id", migration)


if __name__ == "__main__":
    unittest.main()

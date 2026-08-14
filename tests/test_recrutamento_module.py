import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RecrutamentoModuleTests(unittest.TestCase):
    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for nome in (
            "recrutamento_candidatos.html",
            "novo_candidato_recrutamento.html",
        ):
            app.jinja_env.get_template(nome)

    def test_routes_are_registered(self):
        source = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
        self.assertIn("register_recrutamento_routes", source)

    def test_all_module_routes_require_exclusive_permission(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(
            source.count('@module_required("acesso_recrutamento")'),
            3,
        )
        self.assertNotIn("acesso_gestao_pessoas", source)

    def test_permission_is_available_across_user_flows(self):
        usuarios = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )
        autenticacao = (ROOT / "app" / "views" / "autenticacao.py").read_text(
            encoding="utf-8"
        )
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(usuarios.count("acesso_recrutamento"), 12)
        self.assertIn("session['acesso_recrutamento']", autenticacao)
        self.assertIn(
            "session.get('acesso_recrutamento') or is_admin",
            sidebar,
        )

        for template in (
            "usuarios.html",
            "editar_usuario.html",
            "permissoes_usuario.html",
        ):
            source = (ROOT / "app" / "templates" / template).read_text(
                encoding="utf-8"
            )
            self.assertIn('name="acesso_recrutamento"', source)

    def test_schema_separates_candidate_and_application(self):
        migration = (
            ROOT / "docs" / "criar_modulo_recrutamento.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("recrutamento_candidatos (", migration)
        self.assertIn("UNIQUE (cpf)", migration)
        self.assertIn("recrutamento_candidaturas (", migration)
        self.assertIn("recrutamento_etapas (", migration)
        self.assertIn("recrutamento_pre_admissao (", migration)
        self.assertIn("recrutamento_historico (", migration)

    def test_cpf_validation(self):
        from app.views.recrutamento import cpf_valido

        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertFalse(cpf_valido("123"))

    def test_phone_validation_accepts_mobile_and_landline(self):
        from app.views.recrutamento import telefone_valido

        self.assertTrue(telefone_valido("(31) 99999-1234"))
        self.assertTrue(telefone_valido("(31) 3333-1234"))
        self.assertFalse(telefone_valido("9999-1234"))
        self.assertFalse(telefone_valido("(00) 99999-1234"))

    def test_alternative_phone_is_modeled_and_masked(self):
        view = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "novo_candidato_recrutamento.html"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "adicionar_telefone_alternativo_recrutamento.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("telefone_alternativo", view)
        self.assertIn('name="telefone_alternativo"', template)
        self.assertIn("formatarCpf", template)
        self.assertIn("formatarTelefone", template)
        self.assertIn("telefone_alternativo", migration)


if __name__ == "__main__":
    unittest.main()

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CadastroUsuariosSqlTests(unittest.TestCase):
    def test_insert_de_usuario_tem_um_parametro_por_marcador(self):
        source = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)

        inserts = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) < 2:
                continue
            sql_arg, params_arg = node.args[:2]
            if not isinstance(sql_arg, ast.Constant):
                continue
            if "INSERT INTO usuarios (" not in str(sql_arg.value):
                continue
            if not isinstance(params_arg, (ast.Tuple, ast.List)):
                continue
            inserts.append((str(sql_arg.value), params_arg.elts))

        self.assertEqual(1, len(inserts))
        sql, params = inserts[0]
        self.assertEqual(
            sql.count("%s"),
            len(params),
            "O INSERT de usuarios possui quantidade diferente de "
            "marcadores e parâmetros.",
        )

    def test_listagem_tem_busca_e_paginacao_no_servidor(self):
        source = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("u.nome LIKE %s OR u.matricula LIKE %s", source)
        self.assertIn("SELECT COUNT(*) AS total", source)
        self.assertIn("LIMIT %s OFFSET %s", source)
        self.assertIn("per_page not in {20, 50, 100}", source)

    def test_template_da_listagem_compila_e_usa_acoes_minimalistas(self):
        from app import create_app

        app = create_app()
        app.jinja_env.get_template("listar_usuarios.html")

        template = (
            ROOT / "app" / "templates" / "listar_usuarios.html"
        ).read_text(encoding="utf-8")
        self.assertIn('name="busca"', template)
        self.assertIn('class="pagination pagination-sm mb-0"', template)
        self.assertIn('aria-label="Aplicar filtros"', template)
        self.assertIn('aria-label="Limpar filtros"', template)
        self.assertIn('aria-label="Novo funcionário"', template)
        self.assertIn('id="listaUsuarios"', template)
        self.assertIn('id="usuarios-data"', template)
        self.assertIn("configurarBuscaUsuario", template)
        self.assertNotIn("Busca: {{ filtros.get('busca') }}", template)


if __name__ == "__main__":
    unittest.main()




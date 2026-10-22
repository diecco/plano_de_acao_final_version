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


if __name__ == "__main__":
    unittest.main()

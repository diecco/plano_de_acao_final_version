import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTES_PATH = PROJECT_ROOT / "app" / "routes.py"
TRAINING_ROUTES_PATH = PROJECT_ROOT / "app" / "views" / "treinamentos.py"
ROUTE_DECORATOR_PATHS = (
    ROUTES_PATH,
    TRAINING_ROUTES_PATH,
    PROJECT_ROOT / "app" / "views" / "agenda_ssma.py",
    PROJECT_ROOT / "app" / "views" / "recusa_tarefa.py",
)
PCPM_ROUTE_PATHS = (
    PROJECT_ROOT / "app" / "routes.py",
    PROJECT_ROOT / "app" / "views" / "pcpm_cadastros.py",
    PROJECT_ROOT / "app" / "views" / "pcpm_checklist.py",
    PROJECT_ROOT / "app" / "views" / "pcpm_equipamentos.py",
    PROJECT_ROOT / "app" / "views" / "pcpm_movimentacoes.py",
)
DECORATORS_PATH = PROJECT_ROOT / "app" / "decorators.py"


fake_session = {}


def fake_redirect(location):
    return types.SimpleNamespace(status_code=302, location=location)


fake_flask = types.ModuleType("flask")
fake_flask.flash = lambda *args, **kwargs: None
fake_flask.jsonify = lambda value: value
fake_flask.redirect = fake_redirect
fake_flask.session = fake_session
fake_flask.url_for = lambda endpoint: "/dashboard"

previous_flask = sys.modules.get("flask")
sys.modules["flask"] = fake_flask
spec = importlib.util.spec_from_file_location(
    "permission_decorators",
    DECORATORS_PATH,
)
permission_decorators = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permission_decorators)
if previous_flask is None:
    del sys.modules["flask"]
else:
    sys.modules["flask"] = previous_flask

gerenciar_agendamentos_ssma_required = (
    permission_decorators.gerenciar_agendamentos_ssma_required
)
lider_ssma_required = permission_decorators.lider_ssma_required
api_module_required = permission_decorators.api_module_required
login_required = permission_decorators.login_required
module_required = permission_decorators.module_required


def route_decorators():
    tree = ast.parse(ROUTES_PATH.read_text(encoding="utf-8"))
    result = {}

    for route_path in ROUTE_DECORATOR_PATHS:
        route_tree = ast.parse(route_path.read_text(encoding="utf-8"))
        for node in ast.walk(route_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            has_route = any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "route"
                for decorator in node.decorator_list
            )

            if has_route:
                result[node.name] = [ast.unparse(item) for item in node.decorator_list]

    return result, tree


def routes_by_function():
    result = {}

    for route_path in PCPM_ROUTE_PATHS:
        tree = ast.parse(route_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            paths = []
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "route"
                ):
                    paths.append(ast.literal_eval(decorator.args[0]))

            if paths:
                result[node.name] = {
                    "paths": paths,
                    "decorators": [ast.unparse(item) for item in node.decorator_list],
                }

    return result


class RoutePermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decorators, cls.tree = route_decorators()

    def assert_route_uses(self, function_name, decorator):
        self.assertIn(function_name, self.decorators)
        self.assertIn(decorator, self.decorators[function_name])

    def test_login_required_is_not_redefined_in_routes(self):
        local_functions = {
            node.name
            for node in self.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertNotIn("login_required", local_functions)

    def test_ssma_refusal_listing_requires_ssma_module(self):
        self.assert_route_uses("listar_recusa", "module_required('acesso_ssma')")

    def test_training_exports_require_training_module(self):
        functions = (
            "exportar_treinamentos_realizados_excel",
            "exportar_treinamentos_a_vencer_excel",
            "exportar_treinamentos_vencidos_excel",
            "exportar_treinamentos_pendentes_excel",
        )
        for function_name in functions:
            with self.subTest(function_name=function_name):
                self.assert_route_uses(
                    function_name,
                    "module_required('acesso_treinamentos')",
                )

    def test_training_full_mutations_require_advanced_profile(self):
        for function_name in ("editar_treinamento", "excluir_treinamento"):
            with self.subTest(function_name=function_name):
                self.assert_route_uses(
                    function_name,
                    "perfil_required('avancado')",
                )

    def test_training_report_screens_use_central_scope(self):
        source = TRAINING_ROUTES_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name: ast.get_source_segment(source, node) or ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        report_functions = (
            "relatorio_treinamentos_realizados",
            "relatorio_treinamentos_a_vencer",
            "relatorio_treinamentos_vencidos",
            "relatorio_treinamentos_pendentes",
        )
        for function_name in report_functions:
            with self.subTest(function_name=function_name):
                function_source = functions[function_name]
                self.assertIn(
                    "_rt_buscar_usuarios_permitidos",
                    function_source,
                )
                self.assertIn(
                    "filtrar_usuario_ids_permitidos",
                    function_source,
                )

    def test_ssma_calendar_routes_require_leader_permission(self):
        for function_name in ("meu_calendario_ssma", "executar_agendamento_ssma"):
            with self.subTest(function_name=function_name):
                self.assert_route_uses(function_name, "lider_ssma_required")

    def test_adherence_report_requires_schedule_management_permission(self):
        self.assert_route_uses(
            "relatorio_aderencia_ssma",
            "gerenciar_agendamentos_ssma_required",
        )

    def test_all_pcpm_routes_require_pcpm_module(self):
        routes = routes_by_function()
        pcpm_routes = {
            function_name: route
            for function_name, route in routes.items()
            if any(
                "pcpm" in path.lower() or "equipamento" in path.lower()
                for path in route["paths"]
            )
        }

        self.assertTrue(pcpm_routes)
        for function_name, route in pcpm_routes.items():
            with self.subTest(function_name=function_name):
                expected_decorator = (
                    "api_module_required('acesso_pcpm')"
                    if any(path.startswith("/api/") for path in route["paths"])
                    else "module_required('acesso_pcpm')"
                )
                self.assertIn(
                    expected_decorator,
                    route["decorators"],
                )


class DecoratorBehaviorTests(unittest.TestCase):
    def setUp(self):
        fake_session.clear()

    def call_with_session(self, decorated, values):
        fake_session.clear()
        fake_session.update(values)
        return decorated()

    def test_module_permission_allows_flag(self):
        decorated = module_required("acesso_ssma")(lambda: "ok")
        self.assertEqual(
            self.call_with_session(decorated, {"acesso_ssma": True}),
            "ok",
        )

    def test_module_permission_allows_administrator(self):
        decorated = module_required("acesso_ssma")(lambda: "ok")
        self.assertEqual(
            self.call_with_session(decorated, {"perfil": "administrador"}),
            "ok",
        )

    def test_schedule_manager_permission_allows_flag(self):
        decorated = gerenciar_agendamentos_ssma_required(lambda: "ok")
        self.assertEqual(
            self.call_with_session(
                decorated,
                {"pode_criar_agendamento_ssma": True},
            ),
            "ok",
        )

    def test_schedule_manager_permission_allows_administrator(self):
        decorated = gerenciar_agendamentos_ssma_required(lambda: "ok")
        self.assertEqual(
            self.call_with_session(decorated, {"perfil": "administrador"}),
            "ok",
        )

    def test_schedule_manager_permission_denies_unprivileged_user(self):
        decorated = gerenciar_agendamentos_ssma_required(lambda: "ok")
        response = self.call_with_session(decorated, {})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/dashboard"))

    def test_ssma_leader_permission_requires_explicit_flag(self):
        decorated = lider_ssma_required(lambda: "ok")
        self.assertEqual(
            self.call_with_session(
                decorated,
                {"pode_ser_lider_ssma": True},
            ),
            "ok",
        )

        response = self.call_with_session(
            decorated,
            {"perfil": "administrador"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/dashboard"))

    def test_api_module_permission_preserves_json_403_contract(self):
        decorated = api_module_required("acesso_pcpm")(lambda: "ok")
        payload, status_code = self.call_with_session(decorated, {})
        self.assertEqual(status_code, 403)
        self.assertFalse(payload["sucesso"])

    def test_api_module_permission_allows_administrator(self):
        decorated = api_module_required("acesso_pcpm")(lambda: "ok")
        self.assertEqual(
            self.call_with_session(decorated, {"perfil": "administrador"}),
            "ok",
        )

    def test_login_rejects_unknown_profile(self):
        decorated = login_required(lambda: "ok")
        response = self.call_with_session(
            decorated,
            {"usuario_id": 1, "perfil": "desconhecido"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))
        self.assertEqual(fake_session, {})

    def test_login_rejects_intermediate_without_cost_center(self):
        decorated = login_required(lambda: "ok")
        response = self.call_with_session(
            decorated,
            {"usuario_id": 1, "perfil": "intermediario"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))
        self.assertEqual(fake_session, {})

    def test_login_allows_global_profile_without_cost_center(self):
        decorated = login_required(lambda: "ok")
        self.assertEqual(
            self.call_with_session(
                decorated,
                {"usuario_id": 1, "perfil": "administrador"},
            ),
            "ok",
        )

    def test_record_helpers_reject_intermediate_without_cost_center(self):
        class Cursor:
            def execute(self, *args, **kwargs):
                pass

            def fetchone(self):
                return {
                    "id": 1,
                    "centro_custos_responsavel_id": None,
                    "centro_custos_autor_id": None,
                }

        cursor = Cursor()
        fake_session.update({
            "usuario_id": 1,
            "perfil": "intermediario",
            "centro_custos_id": None,
        })

        self.assertIsNone(
            permission_decorators.pode_acessar_acao(cursor, 1)
        )
        self.assertIsNone(
            permission_decorators.pode_acessar_ssma(cursor, "ifs", 1)
        )


if __name__ == "__main__":
    unittest.main()

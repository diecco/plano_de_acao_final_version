import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERMISSIONS_PATH = PROJECT_ROOT / "app" / "permissions.py"

spec = importlib.util.spec_from_file_location(
    "application_permissions",
    PERMISSIONS_PATH,
)
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class TrainingScopeTests(unittest.TestCase):
    def test_administrator_and_advanced_have_global_scope(self):
        for perfil in ("administrador", "avancado"):
            with self.subTest(perfil=perfil):
                self.assertEqual(
                    permissions.resolver_escopo_usuarios_treinamento(
                        perfil,
                        centro_custos_id=10,
                        usuario_id=20,
                    ),
                    {},
                )

    def test_intermediate_is_limited_to_cost_center(self):
        self.assertEqual(
            permissions.resolver_escopo_usuarios_treinamento(
                "intermediario",
                centro_custos_id=10,
                usuario_id=20,
            ),
            {"centro_custos_id": 10},
        )

    def test_basic_is_limited_to_current_user(self):
        self.assertEqual(
            permissions.resolver_escopo_usuarios_treinamento(
                "basico",
                centro_custos_id=10,
                usuario_id=20,
            ),
            {"usuario_id": 20},
        )

    def test_missing_scope_fails_closed(self):
        self.assertEqual(
            permissions.resolver_escopo_usuarios_treinamento(
                "intermediario",
                centro_custos_id=None,
                usuario_id=20,
            ),
            {"centro_custos_id": -1},
        )
        self.assertEqual(
            permissions.resolver_escopo_usuarios_treinamento(
                "basico",
                centro_custos_id=10,
                usuario_id=None,
            ),
            {"usuario_id": -1},
        )

    def test_requested_ids_are_intersected_with_allowed_ids(self):
        self.assertEqual(
            permissions.filtrar_usuario_ids_permitidos(
                usuario_ids_solicitados=[1, 3, 99],
                usuario_ids_permitidos=[1, 2, 3],
            ),
            [1, 3],
        )

    def test_empty_or_invalid_scope_never_means_all_users(self):
        self.assertEqual(
            permissions.filtrar_usuario_ids_permitidos([], []),
            [-1],
        )
        self.assertEqual(
            permissions.filtrar_usuario_ids_permitidos([99], [1, 2]),
            [-1],
        )


if __name__ == "__main__":
    unittest.main()

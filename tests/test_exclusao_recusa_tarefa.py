import unittest
from unittest.mock import MagicMock, patch


class ExclusaoRecusaTarefaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app

        cls.app = create_app()
        cls.app.config.update(TESTING=True, SECRET_KEY="teste")

    def _autenticar(self, client):
        with client.session_transaction() as sessao:
            sessao["usuario_id"] = 1
            sessao["perfil"] = "administrador"

    def test_exclusao_autorizada_confirma_e_fecha_conexao(self):
        conexao = MagicMock()
        cursor = MagicMock()
        conexao.cursor.return_value = cursor

        with self.app.test_client() as client:
            self._autenticar(client)
            with patch(
                "app.views.recusa_tarefa.get_db_connection",
                return_value=conexao,
            ), patch(
                "app.views.recusa_tarefa.pode_acessar_ssma",
                return_value={"id": 17},
            ):
                resposta = client.post("/excluir_recusa/17")

        self.assertEqual(resposta.status_code, 302)
        cursor.execute.assert_called_once_with(
            "DELETE FROM recusa_tarefa WHERE id = %s",
            (17,),
        )
        conexao.commit.assert_called_once_with()
        conexao.rollback.assert_not_called()
        cursor.close.assert_called_once_with()
        conexao.close.assert_called_once_with()

    def test_falha_na_exclusao_faz_rollback_e_fecha_conexao(self):
        conexao = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = RuntimeError("falha simulada")
        conexao.cursor.return_value = cursor

        with self.app.test_client() as client:
            self._autenticar(client)
            with patch(
                "app.views.recusa_tarefa.get_db_connection",
                return_value=conexao,
            ), patch(
                "app.views.recusa_tarefa.pode_acessar_ssma",
                return_value={"id": 18},
            ):
                resposta = client.post("/excluir_recusa/18")

        self.assertEqual(resposta.status_code, 302)
        conexao.commit.assert_not_called()
        conexao.rollback.assert_called_once_with()
        cursor.close.assert_called_once_with()
        conexao.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

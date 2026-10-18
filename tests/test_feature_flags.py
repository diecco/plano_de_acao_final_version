import os
import unittest
from unittest.mock import patch

from flask import Flask

from app.feature_flags import register_feature_flags


class FeatureFlagsTestCase(unittest.TestCase):
    def criar_app(self, env=None):
        app = Flask(__name__)

        @app.route("/observacoes", endpoint="main.observacoes_comportamentais")
        def observacoes():
            return "observacoes"

        @app.route("/desvios", endpoint="main.listar_desvios")
        def desvios():
            return "desvios"

        @app.route("/inicio", endpoint="main.inicio")
        def inicio():
            return "inicio"

        with patch.dict(os.environ, env or {}, clear=False):
            register_feature_flags(app)

        return app

    def test_features_ficam_ativas_por_padrao(self):
        app = self.criar_app()
        client = app.test_client()

        self.assertEqual(client.get("/observacoes").status_code, 200)
        self.assertEqual(client.get("/desvios").status_code, 200)
        self.assertFalse(app.config["OBSERVACAO_COMPORTAMENTAL_READ_ONLY"])

    def test_features_desativadas_bloqueiam_urls_diretas(self):
        app = self.criar_app({
            "FEATURE_OBSERVACAO_COMPORTAMENTAL_ENABLED": "false",
            "FEATURE_RELATO_DESVIOS_ENABLED": "false",
        })
        client = app.test_client()

        self.assertEqual(client.get("/observacoes").status_code, 404)
        self.assertEqual(client.get("/desvios").status_code, 404)
        self.assertEqual(client.get("/inicio").status_code, 200)

    def test_contexto_dos_templates_reflete_as_flags(self):
        app = self.criar_app({
            "FEATURE_OBSERVACAO_COMPORTAMENTAL_ENABLED": "false",
            "FEATURE_RELATO_DESVIOS_ENABLED": "true",
        })

        with app.test_request_context("/inicio"):
            contexto = {}
            for processor in app.template_context_processors[None]:
                contexto.update(processor())

        self.assertFalse(contexto["feature_observacao_comportamental_enabled"])
        self.assertTrue(contexto["feature_relato_desvios_enabled"])


if __name__ == "__main__":
    unittest.main()

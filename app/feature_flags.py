import os

from flask import abort, current_app, request


FEATURE_OBSERVACAO_COMPORTAMENTAL = "observacao_comportamental"
FEATURE_RELATO_DESVIOS = "relato_desvios"

_ENV_BY_FEATURE = {
    FEATURE_OBSERVACAO_COMPORTAMENTAL: "FEATURE_OBSERVACAO_COMPORTAMENTAL_ENABLED",
    FEATURE_RELATO_DESVIOS: "FEATURE_RELATO_DESVIOS_ENABLED",
}

_ENDPOINTS_BY_FEATURE = {
    FEATURE_OBSERVACAO_COMPORTAMENTAL: {
        "main.observacoes_comportamentais",
        "main.nova_observacao_comportamental",
        "main.detalhar_observacao_comportamental",
        "main.editar_observacao_comportamental",
        "main.excluir_observacao_comportamental",
        "main.cancelar_observacao_comportamental",
        "main.reabrir_observacao_comportamental",
    },
    FEATURE_RELATO_DESVIOS: {
        "main.analisar_desvio_ia",
        "main.listar_desvios",
        "main.novo_desvio",
        "main.editar_desvio",
        "main.excluir_desvio",
        "main.buffer_desvios",
        "main.detalhar_desvio",
        "main.direcionar_desvio",
        "main.baixar_anexo_desvio",
    },
}


def _env_enabled(name):
    return os.getenv(name, "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def feature_enabled(feature):
    config_key = f"FEATURE_{feature.upper()}_ENABLED"
    return bool(current_app.config.get(config_key, True))


def register_feature_flags(app):
    for feature, env_name in _ENV_BY_FEATURE.items():
        config_key = f"FEATURE_{feature.upper()}_ENABLED"
        app.config[config_key] = _env_enabled(env_name)

    @app.context_processor
    def inject_feature_flags():
        return {
            "feature_observacao_comportamental_enabled": feature_enabled(
                FEATURE_OBSERVACAO_COMPORTAMENTAL
            ),
            "feature_relato_desvios_enabled": feature_enabled(FEATURE_RELATO_DESVIOS),
        }

    @app.before_request
    def block_disabled_features():
        endpoint = request.endpoint
        if not endpoint:
            return None

        for feature, endpoints in _ENDPOINTS_BY_FEATURE.items():
            if endpoint in endpoints and not feature_enabled(feature):
                abort(404)

        return None

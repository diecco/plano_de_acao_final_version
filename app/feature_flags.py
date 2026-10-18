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
        "main.importar_observacoes_fluig",
        "main.detalhar_observacao_fluig",
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


def _env_enabled(name, default=True):
    default_value = "true" if default else "false"
    return os.getenv(name, default_value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def feature_enabled(feature):
    config_key = f"FEATURE_{feature.upper()}_ENABLED"
    return bool(current_app.config.get(config_key, True))


def observacao_comportamental_read_only():
    return bool(current_app.config.get("OBSERVACAO_COMPORTAMENTAL_READ_ONLY", False))


def register_feature_flags(app):
    for feature, env_name in _ENV_BY_FEATURE.items():
        config_key = f"FEATURE_{feature.upper()}_ENABLED"
        app.config[config_key] = _env_enabled(env_name)
    app.config["OBSERVACAO_COMPORTAMENTAL_READ_ONLY"] = _env_enabled(
        "OBSERVACAO_COMPORTAMENTAL_READ_ONLY", default=False
    )

    @app.context_processor
    def inject_feature_flags():
        return {
            "feature_observacao_comportamental_enabled": feature_enabled(
                FEATURE_OBSERVACAO_COMPORTAMENTAL
            ),
            "feature_relato_desvios_enabled": feature_enabled(FEATURE_RELATO_DESVIOS),
            "observacao_comportamental_read_only": (
                observacao_comportamental_read_only()
            ),
        }

    @app.before_request
    def block_disabled_features():
        endpoint = request.endpoint
        if not endpoint:
            return None

        for feature, endpoints in _ENDPOINTS_BY_FEATURE.items():
            if endpoint in endpoints and not feature_enabled(feature):
                abort(404)

        if observacao_comportamental_read_only() and endpoint in {
            "main.nova_observacao_comportamental",
            "main.editar_observacao_comportamental",
            "main.excluir_observacao_comportamental",
            "main.cancelar_observacao_comportamental",
            "main.reabrir_observacao_comportamental",
        }:
            abort(405)

        return None

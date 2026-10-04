-- Executar primeiro na base de HOMOLOGAÇÃO, após criar_modulo_desvios.sql.

ALTER TABLE desvios
    ADD COLUMN matriz_exposicao VARCHAR(20) NULL AFTER matriz_grave,
    ADD COLUMN matriz_controles VARCHAR(20) NULL AFTER matriz_exposicao,
    ADD COLUMN matriz_ocorrencia VARCHAR(20) NULL AFTER matriz_controles,
    ADD COLUMN probabilidade VARCHAR(10) NULL AFTER potencial,
    ADD COLUMN nivel_risco VARCHAR(10) NULL AFTER probabilidade,
    ADD COLUMN ia_utilizada TINYINT(1) NOT NULL DEFAULT 0 AFTER nivel_risco,
    ADD COLUMN ia_modelo VARCHAR(100) NULL AFTER ia_utilizada,
    ADD COLUMN ia_descricao_original TEXT NULL AFTER ia_modelo,
    ADD COLUMN ia_descricao_sugerida TEXT NULL AFTER ia_descricao_original,
    ADD COLUMN ia_severidade_sugerida CHAR(1) NULL AFTER ia_descricao_sugerida,
    ADD COLUMN ia_probabilidade_sugerida VARCHAR(10) NULL AFTER ia_severidade_sugerida,
    ADD COLUMN ia_justificativa TEXT NULL AFTER ia_probabilidade_sugerida,
    ADD COLUMN ia_confianca TINYINT UNSIGNED NULL AFTER ia_justificativa;

-- Registros anteriores permanecem válidos; a nova matriz é exigida somente nos novos relatos.

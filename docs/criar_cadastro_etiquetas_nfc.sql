-- Cadastro de etiquetas NFC para os checklists configuráveis.
-- Migração aditiva e reexecutável no schema trackplan_teste.

CREATE TABLE IF NOT EXISTS nfc_etiquetas (
    id INT NOT NULL AUTO_INCREMENT,
    numero VARCHAR(80) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    token VARCHAR(64) NOT NULL,
    abrangencia ENUM('global', 'centros') NOT NULL DEFAULT 'global',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_por INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NULL DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_nfc_etiquetas_numero (numero),
    UNIQUE KEY uk_nfc_etiquetas_token (token),
    KEY idx_nfc_etiquetas_status (ativo, abrangencia),
    CONSTRAINT fk_nfc_etiquetas_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS nfc_etiquetas_centros (
    etiqueta_id INT NOT NULL,
    centro_custos_id INT NOT NULL,
    PRIMARY KEY (etiqueta_id, centro_custos_id),
    KEY idx_nfc_etiquetas_centros_cc (centro_custos_id),
    CONSTRAINT fk_nfc_etiquetas_centros_etiqueta
        FOREIGN KEY (etiqueta_id) REFERENCES nfc_etiquetas (id) ON DELETE CASCADE,
    CONSTRAINT fk_nfc_etiquetas_centros_centro
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

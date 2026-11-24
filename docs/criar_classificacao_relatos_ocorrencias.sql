-- Classificação do potencial dos Relatos de Ocorrências.
-- Execute no schema de destino após criar_importacao_relatos_ocorrencias.sql.

CREATE TABLE IF NOT EXISTS relatos_ocorrencias_classificacoes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    relato_id BIGINT NOT NULL,
    severidade CHAR(1) NOT NULL,
    matriz_exposicao VARCHAR(10) NOT NULL,
    matriz_controles VARCHAR(10) NOT NULL,
    matriz_ocorrencia VARCHAR(10) NOT NULL,
    probabilidade VARCHAR(10) NOT NULL,
    nivel_risco VARCHAR(10) NOT NULL,
    justificativa TEXT NOT NULL,
    classificado_por INT NOT NULL,
    classificado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_por INT NULL,
    atualizado_em DATETIME NULL,
    UNIQUE KEY uk_rel_oc_class_relato (relato_id),
    KEY idx_rel_oc_class_severidade (severidade),
    KEY idx_rel_oc_class_usuario (classificado_por),
    CONSTRAINT fk_rel_oc_class_relato FOREIGN KEY (relato_id)
        REFERENCES relatos_ocorrencias (id) ON DELETE CASCADE,
    CONSTRAINT fk_rel_oc_class_usuario FOREIGN KEY (classificado_por)
        REFERENCES usuarios (id),
    CONSTRAINT fk_rel_oc_class_atualizador FOREIGN KEY (atualizado_por)
        REFERENCES usuarios (id),
    CONSTRAINT chk_rel_oc_class_severidade CHECK (severidade IN ('A', 'B', 'C')),
    CONSTRAINT chk_rel_oc_class_probabilidade CHECK (probabilidade IN ('baixa', 'media', 'alta')),
    CONSTRAINT chk_rel_oc_class_risco CHECK (nivel_risco IN ('baixo', 'medio', 'alto'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS relatos_ocorrencias_classificacoes_historico (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    classificacao_id BIGINT NOT NULL,
    relato_id BIGINT NOT NULL,
    versao INT NOT NULL,
    severidade CHAR(1) NOT NULL,
    matriz_exposicao VARCHAR(10) NOT NULL,
    matriz_controles VARCHAR(10) NOT NULL,
    matriz_ocorrencia VARCHAR(10) NOT NULL,
    probabilidade VARCHAR(10) NOT NULL,
    nivel_risco VARCHAR(10) NOT NULL,
    justificativa TEXT NOT NULL,
    usuario_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_rel_oc_class_hist_versao (classificacao_id, versao),
    KEY idx_rel_oc_class_hist_relato (relato_id),
    CONSTRAINT fk_rel_oc_class_hist_classificacao FOREIGN KEY (classificacao_id)
        REFERENCES relatos_ocorrencias_classificacoes (id) ON DELETE CASCADE,
    CONSTRAINT fk_rel_oc_class_hist_relato FOREIGN KEY (relato_id)
        REFERENCES relatos_ocorrencias (id) ON DELETE CASCADE,
    CONSTRAINT fk_rel_oc_class_hist_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

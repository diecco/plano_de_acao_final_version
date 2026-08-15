-- Histórico imutável dos ciclos anteriores de uma candidatura.
-- Execute no schema de homologação antes de publicar o código.

CREATE TABLE IF NOT EXISTS recrutamento_ciclos_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    numero_ciclo SMALLINT UNSIGNED NOT NULL,
    cargo_id INT NULL,
    cargo_pretendido VARCHAR(160) NOT NULL,
    exige_teste_pratico VARCHAR(30) NOT NULL,
    status VARCHAR(40) NOT NULL,
    decisao_resultado VARCHAR(40) NULL,
    decisao_parecer TEXT NULL,
    decisao_por INT NULL,
    decisao_em DATETIME NULL,
    justificativa_reaproveitamento TEXT NOT NULL,
    arquivado_por INT NOT NULL,
    arquivado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_recrutamento_ciclo_historico UNIQUE (candidatura_id, numero_ciclo),
    CONSTRAINT fk_recrutamento_ciclo_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_ciclo_cargo
        FOREIGN KEY (cargo_id) REFERENCES cargos(id) ON DELETE SET NULL,
    CONSTRAINT fk_recrutamento_ciclo_decisao
        FOREIGN KEY (decisao_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT fk_recrutamento_ciclo_arquivado
        FOREIGN KEY (arquivado_por) REFERENCES usuarios(id),
    INDEX idx_recrutamento_ciclo_candidatura (candidatura_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_etapas_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ciclo_historico_id INT NOT NULL,
    etapa_origem_id INT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    nome VARCHAR(160) NOT NULL,
    ordem SMALLINT UNSIGNED NOT NULL,
    obrigatoria TINYINT(1) NOT NULL,
    papel_responsavel VARCHAR(40) NOT NULL,
    avaliador_id INT NULL,
    status VARCHAR(40) NOT NULL,
    resultado VARCHAR(40) NULL,
    parecer TEXT NULL,
    restricao TEXT NULL,
    motivo_dispensa TEXT NULL,
    data_prevista DATETIME NULL,
    realizada_em DATETIME NULL,
    registrado_por INT NULL,
    criado_em DATETIME NULL,
    atualizado_em DATETIME NULL,
    CONSTRAINT fk_recrutamento_etapa_hist_ciclo
        FOREIGN KEY (ciclo_historico_id) REFERENCES recrutamento_ciclos_historico(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_etapa_hist_avaliador
        FOREIGN KEY (avaliador_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT fk_recrutamento_etapa_hist_registrado
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_recrutamento_etapa_hist_ciclo (ciclo_historico_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_complementos_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    etapa_historico_id INT NOT NULL,
    parecer TEXT NOT NULL,
    autor_id INT NULL,
    criado_em DATETIME NULL,
    CONSTRAINT fk_recrutamento_complemento_hist_etapa
        FOREIGN KEY (etapa_historico_id) REFERENCES recrutamento_etapas_historico(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_complemento_hist_autor
        FOREIGN KEY (autor_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_recrutamento_complemento_hist_etapa (etapa_historico_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

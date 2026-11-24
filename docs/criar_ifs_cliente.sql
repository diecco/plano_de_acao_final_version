-- IFS do Cliente - execute no schema de homologacao.
-- Estruturas independentes da IFS interna; o catalogo ifs_blocos/ifs_itens e reutilizado.

CREATE TABLE IF NOT EXISTS ifs_cliente_inspecoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    centro_custos_id INT NOT NULL,
    data_inspecao DATE NOT NULL,
    hora_inspecao TIME NULL,
    local_inspecao VARCHAR(255) NULL,
    participantes TEXT NULL,
    descricao_atividade_os TEXT NULL,
    referencia_cliente VARCHAR(120) NULL,
    total_itens_avaliados INT NOT NULL DEFAULT 0,
    total_nao_conformidades INT NOT NULL DEFAULT 0,
    percentual DECIMAL(6,2) NOT NULL DEFAULT 0,
    conceito VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'plano_aberto',
    criado_por INT NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ifs_cliente_data (data_inspecao),
    INDEX idx_ifs_cliente_status (status),
    CONSTRAINT fk_ifs_cliente_cc FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id),
    CONSTRAINT fk_ifs_cliente_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ifs_cliente_respostas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspecao_id INT NOT NULL,
    item_id INT NOT NULL,
    codigo_item VARCHAR(30) NOT NULL,
    descricao_item TEXT NOT NULL,
    potencial CHAR(1) NOT NULL,
    resultado CHAR(1) NOT NULL,
    UNIQUE KEY uk_ifs_cliente_resposta (inspecao_id, item_id),
    CONSTRAINT fk_ifs_cliente_resposta_inspecao FOREIGN KEY (inspecao_id)
        REFERENCES ifs_cliente_inspecoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_ifs_cliente_resposta_item FOREIGN KEY (item_id) REFERENCES ifs_itens(id),
    CONSTRAINT chk_ifs_cliente_resultado CHECK (resultado IN ('S', 'N')),
    CONSTRAINT chk_ifs_cliente_potencial CHECK (potencial IN ('A', 'B', 'C'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ifs_cliente_desvios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspecao_id INT NOT NULL,
    item_id INT NOT NULL,
    codigo_item VARCHAR(30) NOT NULL,
    descricao_item TEXT NOT NULL,
    potencial CHAR(1) NOT NULL,
    desvio_observado TEXT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ifs_cliente_desvio (inspecao_id, item_id),
    CONSTRAINT fk_ifs_cliente_desvio_inspecao FOREIGN KEY (inspecao_id)
        REFERENCES ifs_cliente_inspecoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_ifs_cliente_desvio_item FOREIGN KEY (item_id) REFERENCES ifs_itens(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ifs_cliente_desvio_acoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    desvio_id INT NOT NULL,
    acao_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ifs_cliente_acao (desvio_id, acao_id),
    CONSTRAINT fk_ifs_cliente_da_desvio FOREIGN KEY (desvio_id)
        REFERENCES ifs_cliente_desvios(id) ON DELETE CASCADE,
    CONSTRAINT fk_ifs_cliente_da_acao FOREIGN KEY (acao_id) REFERENCES acoes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ifs_cliente_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspecao_id INT NOT NULL,
    usuario_id INT NOT NULL,
    evento VARCHAR(80) NOT NULL,
    descricao TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ifs_cliente_hist_inspecao FOREIGN KEY (inspecao_id)
        REFERENCES ifs_cliente_inspecoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_ifs_cliente_hist_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

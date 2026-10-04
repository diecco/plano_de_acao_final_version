-- Executar primeiro na base de HOMOLOGAÇÃO.

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND COLUMN_NAME = 'acesso_desvios'
    ),
    'SELECT 1',
    'ALTER TABLE usuarios ADD COLUMN acesso_desvios TINYINT(1) NOT NULL DEFAULT 0'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'origens'
          AND COLUMN_NAME = 'centro_custos_id'
    ),
    'SELECT 1',
    'ALTER TABLE origens ADD COLUMN centro_custos_id INT NULL'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND COLUMN_NAME = 'pode_direcionar_desvios'
    ),
    'SELECT 1',
    'ALTER TABLE usuarios ADD COLUMN pode_direcionar_desvios TINYINT(1) NOT NULL DEFAULT 0'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS desvios_categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL UNIQUE,
    ordem INT NOT NULL DEFAULT 0,
    ativo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO desvios_categorias (nome, ordem, ativo) VALUES
    ('5S / Organização e limpeza', 10, 1),
    ('EPI', 20, 1),
    ('Procedimento', 30, 1),
    ('Ferramentas e equipamentos', 40, 1),
    ('Bloqueio de energia', 50, 1),
    ('Trabalho em altura', 60, 1),
    ('Trânsito e movimentação', 70, 1),
    ('Ergonomia', 80, 1),
    ('Meio ambiente', 90, 1),
    ('Instalações', 100, 1),
    ('Outros', 999, 1)
ON DUPLICATE KEY UPDATE ordem = VALUES(ordem), ativo = 1;

CREATE TABLE IF NOT EXISTS desvios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    centro_custos_id INT NOT NULL,
    relator_id INT NOT NULL,
    registrado_por INT NOT NULL,
    setor_id INT NOT NULL,
    categoria_id INT NOT NULL,
    data_ocorrencia DATE NOT NULL,
    hora_ocorrencia TIME NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    descricao TEXT NOT NULL,
    matriz_critico TINYINT(1) NOT NULL DEFAULT 0,
    matriz_grave TINYINT(1) NOT NULL DEFAULT 0,
    potencial CHAR(1) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'aguardando_direcionamento',
    acao_id INT NULL,
    direcionado_por INT NULL,
    direcionado_em DATETIME NULL,
    excluido_em DATETIME NULL,
    excluido_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_desvios_buffer (centro_custos_id, status, acao_id),
    KEY idx_desvios_data (centro_custos_id, data_ocorrencia),
    CONSTRAINT fk_desvio_centro FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id),
    CONSTRAINT fk_desvio_relator FOREIGN KEY (relator_id) REFERENCES usuarios(id),
    CONSTRAINT fk_desvio_registrador FOREIGN KEY (registrado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_desvio_setor FOREIGN KEY (setor_id) REFERENCES setores(id),
    CONSTRAINT fk_desvio_categoria FOREIGN KEY (categoria_id) REFERENCES desvios_categorias(id),
    CONSTRAINT fk_desvio_acao FOREIGN KEY (acao_id) REFERENCES acoes(id) ON DELETE SET NULL,
    CONSTRAINT fk_desvio_direcionador FOREIGN KEY (direcionado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_desvio_exclusao FOREIGN KEY (excluido_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS desvios_anexos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    desvio_id INT NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    mime_type VARCHAR(120) NULL,
    criado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_desvio_anexo_registro FOREIGN KEY (desvio_id) REFERENCES desvios(id) ON DELETE CASCADE,
    CONSTRAINT fk_desvio_anexo_usuario FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS desvios_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    desvio_id INT NOT NULL,
    usuario_id INT NOT NULL,
    evento VARCHAR(60) NOT NULL,
    descricao TEXT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_desvio_historico (desvio_id, criado_em),
    CONSTRAINT fk_desvio_historico_registro FOREIGN KEY (desvio_id) REFERENCES desvios(id) ON DELETE CASCADE,
    CONSTRAINT fk_desvio_historico_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

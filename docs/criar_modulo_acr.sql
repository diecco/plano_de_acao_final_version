-- TrackPlan - Fundação do módulo Análise de Causa Raiz (ACR)
-- Ambiente inicial: homologação
-- Compatível com MySQL 8.0+

SET NAMES utf8mb4;

SET @acesso_acr_existe = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'acesso_acr'
);

SET @sql_acesso_acr = IF(
    @acesso_acr_existe = 0,
    'ALTER TABLE usuarios ADD COLUMN acesso_acr TINYINT(1) NOT NULL DEFAULT 0',
    'SELECT ''A coluna usuarios.acesso_acr já existe'' AS informacao'
);

PREPARE stmt_acesso_acr FROM @sql_acesso_acr;
EXECUTE stmt_acesso_acr;
DEALLOCATE PREPARE stmt_acesso_acr;

CREATE TABLE IF NOT EXISTS acr_sequencias (
    ano SMALLINT UNSIGNED NOT NULL,
    ultimo_numero INT UNSIGNED NOT NULL DEFAULT 0,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (ano)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_origens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_origens_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_classificacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(80) NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_classificacoes_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_gravidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(40) NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_gravidades_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_metodologias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL,
    nome VARCHAR(80) NOT NULL,
    implementada TINYINT(1) NOT NULL DEFAULT 0,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_metodologias_codigo (codigo),
    UNIQUE KEY uq_acr_metodologias_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_investigacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ano SMALLINT UNSIGNED NOT NULL,
    sequencial INT UNSIGNED NOT NULL,
    numero VARCHAR(20) NOT NULL,
    origem_id INT NULL,
    origem_outros VARCHAR(255) NULL,
    classificacao_id INT NULL,
    gravidade_id INT NULL,
    metodologia_id INT NULL,
    data_ocorrencia DATE NULL,
    data_investigacao DATE NULL,
    equipamento_processo VARCHAR(255) NULL,
    descricao_ocorrencia TEXT NULL,
    responsavel_id INT NULL,
    criador_id INT NOT NULL,
    centro_custos_id INT NOT NULL,
    superintendencia_id INT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Rascunho',
    data_prevista_eficacia DATE NULL,
    criterio_eficacia TEXT NULL,
    justificativa_cancelamento TEXT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    concluido_em DATETIME NULL,
    cancelado_em DATETIME NULL,
    UNIQUE KEY uq_acr_investigacoes_numero (numero),
    UNIQUE KEY uq_acr_investigacoes_ano_sequencial (ano, sequencial),
    KEY idx_acr_investigacoes_status (status),
    KEY idx_acr_investigacoes_centro (centro_custos_id),
    KEY idx_acr_investigacoes_responsavel (responsavel_id),
    CONSTRAINT fk_acr_investigacoes_origem
        FOREIGN KEY (origem_id) REFERENCES acr_origens(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_acr_investigacoes_classificacao
        FOREIGN KEY (classificacao_id) REFERENCES acr_classificacoes(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_acr_investigacoes_gravidade
        FOREIGN KEY (gravidade_id) REFERENCES acr_gravidades(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_acr_investigacoes_metodologia
        FOREIGN KEY (metodologia_id) REFERENCES acr_metodologias(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_investigacoes_responsavel
        FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_acr_investigacoes_criador
        FOREIGN KEY (criador_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_investigacoes_centro
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_investigacoes_superintendencia
        FOREIGN KEY (superintendencia_id) REFERENCES superintendencias(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_acr_investigacoes_status
        CHECK (status IN (
            'Rascunho',
            'Em Investigação',
            'Aguardando Informações',
            'Concluída',
            'Cancelada'
        ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_participantes (
    investigacao_id INT NOT NULL,
    usuario_id INT NOT NULL,
    adicionado_por INT NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (investigacao_id, usuario_id),
    CONSTRAINT fk_acr_participantes_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_participantes_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_participantes_adicionado_por
        FOREIGN KEY (adicionado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_etapas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    codigo VARCHAR(40) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Não iniciada',
    iniciado_em DATETIME NULL,
    concluido_em DATETIME NULL,
    atualizado_por INT NULL,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_etapas_investigacao_codigo (investigacao_id, codigo),
    CONSTRAINT fk_acr_etapas_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_etapas_atualizado_por
        FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_acr_etapas_status
        CHECK (status IN (
            'Não iniciada',
            'Em andamento',
            'Concluída',
            'Com pendências'
        ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_5_porques (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    ordem TINYINT UNSIGNED NOT NULL,
    pergunta VARCHAR(500) NOT NULL,
    resposta TEXT NULL,
    causa_raiz TINYINT(1) NOT NULL DEFAULT 0,
    respondido_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_5_porques_investigacao_ordem (investigacao_id, ordem),
    CONSTRAINT fk_acr_5_porques_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_5_porques_respondido_por
        FOREIGN KEY (respondido_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_acr_5_porques_ordem CHECK (ordem BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_6m_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    categoria VARCHAR(20) NOT NULL,
    descricao TEXT NOT NULL,
    causa_raiz TINYINT(1) NOT NULL DEFAULT 0,
    classificacao VARCHAR(20) NOT NULL DEFAULT 'potencial',
    justificativa TEXT NULL,
    validacao TEXT NULL,
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    registrado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_acr_6m_investigacao_categoria (
        investigacao_id, categoria, ordem
    ),
    CONSTRAINT fk_acr_6m_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_6m_registrado_por
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_acr_6m_categoria CHECK (categoria IN (
        'metodo', 'maquina', 'mao_obra',
        'material', 'medicao', 'meio_ambiente'
    )),
    CONSTRAINT chk_acr_6m_classificacao CHECK (classificacao IN (
        'potencial', 'descartada', 'contribuinte', 'basica', 'fundamental'
    ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_arvore_causas_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    parent_id INT NULL,
    descricao TEXT NOT NULL,
    classificacao VARCHAR(20) NOT NULL DEFAULT 'potencial',
    ordem SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    registrado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_acr_arvore_investigacao_parent (
        investigacao_id, parent_id, ordem
    ),
    CONSTRAINT fk_acr_arvore_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_arvore_parent
        FOREIGN KEY (parent_id) REFERENCES acr_arvore_causas_itens(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_arvore_registrado_por
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_acr_arvore_classificacao CHECK (classificacao IN (
        'potencial', 'descartada', 'contribuinte', 'basica', 'fundamental'
    ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_causas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    metodologia_id INT NOT NULL,
    descricao TEXT NOT NULL,
    confirmada TINYINT(1) NOT NULL DEFAULT 1,
    identificada_por INT NOT NULL,
    identificada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    invalidada_em DATETIME NULL,
    motivo_invalidacao TEXT NULL,
    CONSTRAINT fk_acr_causas_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_causas_metodologia
        FOREIGN KEY (metodologia_id) REFERENCES acr_metodologias(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_causas_identificada_por
        FOREIGN KEY (identificada_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_acoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    causa_raiz_id INT NULL,
    acao_id INT NOT NULL,
    criado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_acoes_investigacao_acao (investigacao_id, acao_id),
    KEY idx_acr_acoes_acao (acao_id),
    CONSTRAINT fk_acr_acoes_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_acoes_causa
        FOREIGN KEY (causa_raiz_id) REFERENCES acr_causas(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_acr_acoes_acao
        FOREIGN KEY (acao_id) REFERENCES acoes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_acoes_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_verificacoes_eficacia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    ciclo SMALLINT UNSIGNED NOT NULL,
    data_prevista DATE NOT NULL,
    data_realizada DATE NULL,
    criterio TEXT NOT NULL,
    resultado VARCHAR(30) NULL,
    justificativa TEXT NULL,
    responsavel_id INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_acr_verificacoes_investigacao_ciclo (
        investigacao_id,
        ciclo
    ),
    CONSTRAINT fk_acr_verificacoes_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_verificacoes_responsavel
        FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_acr_verificacoes_resultado
        CHECK (
            resultado IS NULL OR resultado IN (
                'Eficaz',
                'Parcialmente eficaz',
                'Ineficaz'
            )
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_evidencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    etapa VARCHAR(40) NULL,
    entidade_tipo VARCHAR(40) NULL,
    entidade_id INT NULL,
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    extensao VARCHAR(15) NOT NULL,
    mime_type VARCHAR(120) NULL,
    tamanho_bytes BIGINT UNSIGNED NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    descricao VARCHAR(500) NULL,
    enviado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em DATETIME NULL,
    excluido_por INT NULL,
    UNIQUE KEY uq_acr_evidencias_nome_armazenado (nome_armazenado),
    KEY idx_acr_evidencias_investigacao (investigacao_id),
    CONSTRAINT fk_acr_evidencias_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_evidencias_enviado_por
        FOREIGN KEY (enviado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_acr_evidencias_excluido_por
        FOREIGN KEY (excluido_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS acr_historico (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    investigacao_id INT NOT NULL,
    usuario_id INT NOT NULL,
    evento VARCHAR(120) NOT NULL,
    etapa VARCHAR(40) NULL,
    entidade_tipo VARCHAR(40) NULL,
    entidade_id INT NULL,
    valor_anterior_json JSON NULL,
    valor_novo_json JSON NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_acr_historico_investigacao_data (
        investigacao_id,
        criado_em
    ),
    CONSTRAINT fk_acr_historico_investigacao
        FOREIGN KEY (investigacao_id) REFERENCES acr_investigacoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_acr_historico_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO acr_origens (nome, ordem) VALUES
    ('Reclamação de cliente', 10),
    ('Não Conformidade Operacional', 20),
    ('Falha de equipamento', 30),
    ('Quebra Recorrente', 40),
    ('Baixa disponibilidade', 50),
    ('Não conformidade SGQ', 60),
    ('Outros', 70);

INSERT IGNORE INTO acr_classificacoes (nome, ordem) VALUES
    ('Segurança', 10),
    ('Qualidade', 20),
    ('Manutenção', 30),
    ('Operação', 40),
    ('Meio Ambiente', 50);

INSERT IGNORE INTO acr_gravidades (nome, ordem) VALUES
    ('Baixa', 10),
    ('Média', 20),
    ('Alta', 30),
    ('Crítica', 40);

INSERT IGNORE INTO acr_metodologias (
    codigo,
    nome,
    implementada,
    ordem
) VALUES
    ('5_porques', '5 Porquês', 1, 10),
    ('arvore_causas', 'Árvore de Causas', 1, 20),
    ('ishikawa', '6M (Ishikawa)', 1, 30),
    ('a3', 'A3', 0, 40);

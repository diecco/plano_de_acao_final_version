-- Módulo de Recrutamento e Seleção - estrutura inicial
-- Execute no schema de homologação antes de testar as telas do módulo.

SET @sql_acesso_recrutamento = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'usuarios'
              AND COLUMN_NAME = 'acesso_recrutamento'
        ),
        'SELECT 1',
        'ALTER TABLE usuarios ADD COLUMN acesso_recrutamento TINYINT(1) NOT NULL DEFAULT 0'
    )
);
PREPARE stmt_acesso_recrutamento FROM @sql_acesso_recrutamento;
EXECUTE stmt_acesso_recrutamento;
DEALLOCATE PREPARE stmt_acesso_recrutamento;

CREATE TABLE IF NOT EXISTS recrutamento_candidatos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpf CHAR(11) NOT NULL,
    nome VARCHAR(160) NOT NULL,
    telefone VARCHAR(30) NOT NULL,
    email VARCHAR(150) NULL,
    cidade VARCHAR(120) NULL,
    estado CHAR(2) NULL,
    curriculo_arquivo VARCHAR(255) NULL,
    observacoes TEXT NULL,
    situacao ENUM('ativo', 'inativo', 'bloqueado') NOT NULL DEFAULT 'ativo',
    criado_por INT NOT NULL,
    atualizado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_recrutamento_candidatos_cpf UNIQUE (cpf),
    CONSTRAINT fk_recrutamento_candidato_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_recrutamento_candidato_atualizado_por
        FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_experiencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidato_id INT NOT NULL,
    ordem TINYINT UNSIGNED NOT NULL,
    empresa VARCHAR(160) NOT NULL,
    cargo VARCHAR(160) NOT NULL,
    data_inicio DATE NULL,
    data_fim DATE NULL,
    emprego_atual TINYINT(1) NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_recrutamento_experiencia_ordem
        UNIQUE (candidato_id, ordem),
    CONSTRAINT fk_recrutamento_experiencia_candidato
        FOREIGN KEY (candidato_id) REFERENCES recrutamento_candidatos(id)
        ON DELETE CASCADE,
    CONSTRAINT chk_recrutamento_experiencia_ordem
        CHECK (ordem BETWEEN 1 AND 3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_candidaturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidato_id INT NOT NULL,
    cargo_id INT NULL,
    cargo_pretendido VARCHAR(160) NOT NULL,
    centro_custos_id INT NOT NULL,
    origem ENUM(
        'sine', 'vagas_com', 'indeed', 'curriculo_presencial',
        'indicacao_funcionario', 'outra_indicacao', 'outros'
    ) NOT NULL,
    detalhe_origem VARCHAR(255) NULL,
    responsavel_rh_id INT NOT NULL,
    exige_teste_pratico ENUM('nao_aplicavel', 'obrigatorio', 'recomendado')
        NOT NULL DEFAULT 'nao_aplicavel',
    status ENUM(
        'cadastrado', 'em_triagem', 'aguardando_entrevista_rh',
        'aguardando_entrevista_gestor', 'em_avaliacao', 'stand_by',
        'reprovado', 'aguardando_proposta', 'proposta_enviada',
        'proposta_recusada', 'em_pre_admissao', 'aguardando_aso',
        'aguardando_documentos', 'liberado_admissao', 'encerrado',
        'desistente'
    ) NOT NULL DEFAULT 'cadastrado',
    data_entrada DATE NOT NULL,
    encerrado_em DATETIME NULL,
    criado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_recrutamento_candidatura_candidato
        FOREIGN KEY (candidato_id) REFERENCES recrutamento_candidatos(id),
    CONSTRAINT fk_recrutamento_candidatura_cargo
        FOREIGN KEY (cargo_id) REFERENCES cargos(id) ON DELETE SET NULL,
    CONSTRAINT fk_recrutamento_candidatura_cc
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id),
    CONSTRAINT fk_recrutamento_candidatura_responsavel
        FOREIGN KEY (responsavel_rh_id) REFERENCES usuarios(id),
    CONSTRAINT fk_recrutamento_candidatura_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id),
    INDEX idx_recrutamento_candidatura_status (status),
    INDEX idx_recrutamento_candidatura_cc (centro_custos_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_etapas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    tipo ENUM(
        'entrevista_comportamental', 'entrevista_tecnica',
        'teste_pratico', 'avaliacao_perfil', 'psicotecnico', 'outra'
    ) NOT NULL,
    nome VARCHAR(160) NOT NULL,
    ordem SMALLINT UNSIGNED NOT NULL,
    obrigatoria TINYINT(1) NOT NULL DEFAULT 1,
    papel_responsavel ENUM('rh', 'gestor', 'profissional_habilitado', 'externo')
        NOT NULL,
    avaliador_id INT NULL,
    status ENUM('pendente', 'agendada', 'realizada', 'dispensada', 'cancelada')
        NOT NULL DEFAULT 'pendente',
    resultado ENUM(
        'aprovado', 'aprovado_restricao', 'reprovado',
        'stand_by', 'nao_realizado', 'dispensado'
    ) NULL,
    parecer TEXT NULL,
    restricao TEXT NULL,
    motivo_dispensa TEXT NULL,
    data_prevista DATETIME NULL,
    realizada_em DATETIME NULL,
    registrado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_recrutamento_etapa_ordem UNIQUE (candidatura_id, ordem),
    CONSTRAINT fk_recrutamento_etapa_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_etapa_avaliador
        FOREIGN KEY (avaliador_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT fk_recrutamento_etapa_registrado_por
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_propostas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    cargo VARCHAR(160) NOT NULL,
    salario DECIMAL(12,2) NOT NULL,
    beneficios TEXT NULL,
    jornada_escala VARCHAR(160) NULL,
    local_trabalho VARCHAR(160) NULL,
    enviada_em DATETIME NULL,
    validade DATE NULL,
    meio_envio VARCHAR(80) NULL,
    status ENUM('elaboracao', 'enviada', 'aceita', 'recusada', 'expirada', 'negociacao')
        NOT NULL DEFAULT 'elaboracao',
    respondida_em DATETIME NULL,
    motivo_recusa TEXT NULL,
    observacoes TEXT NULL,
    criado_por INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_recrutamento_proposta_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id),
    CONSTRAINT fk_recrutamento_proposta_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_pre_admissao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    aso_status ENUM(
        'aguardando_agendamento', 'agendado', 'aguardando_resultado',
        'apto', 'inapto', 'avaliacao_complementar'
    ) NOT NULL DEFAULT 'aguardando_agendamento',
    aso_encaminhado_em DATE NULL,
    aso_data_prevista DATE NULL,
    aso_resultado_em DATE NULL,
    documentos_status ENUM('nao_iniciado', 'pendente', 'completo')
        NOT NULL DEFAULT 'nao_iniciado',
    liberado_admissao_em DATETIME NULL,
    liberado_por INT NULL,
    observacoes TEXT NULL,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_recrutamento_pre_admissao UNIQUE (candidatura_id),
    CONSTRAINT fk_recrutamento_pre_admissao_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id),
    CONSTRAINT fk_recrutamento_pre_admissao_liberado_por
        FOREIGN KEY (liberado_por) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_tipos_documento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(160) NOT NULL UNIQUE,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_documentos_candidatura (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    tipo_documento_id INT NOT NULL,
    obrigatorio TINYINT(1) NOT NULL DEFAULT 1,
    status ENUM('solicitado', 'recebido', 'conferido', 'correcao', 'dispensado')
        NOT NULL DEFAULT 'solicitado',
    recebido_em DATETIME NULL,
    conferido_em DATETIME NULL,
    conferido_por INT NULL,
    observacoes VARCHAR(500) NULL,
    CONSTRAINT uk_recrutamento_documento_candidatura
        UNIQUE (candidatura_id, tipo_documento_id),
    CONSTRAINT fk_recrutamento_documento_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_documento_tipo
        FOREIGN KEY (tipo_documento_id) REFERENCES recrutamento_tipos_documento(id),
    CONSTRAINT fk_recrutamento_documento_conferido_por
        FOREIGN KEY (conferido_por) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recrutamento_historico (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    evento VARCHAR(100) NOT NULL,
    descricao TEXT NULL,
    usuario_id INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recrutamento_historico_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_historico_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_recrutamento_historico_data (candidatura_id, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

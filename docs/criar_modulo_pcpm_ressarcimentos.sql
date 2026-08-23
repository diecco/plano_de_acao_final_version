-- Módulo PCP-M / Ressarcimentos
-- Execute no schema correto e confirme antes com SELECT DATABASE();

ALTER TABLE usuarios
    ADD COLUMN acesso_pcpm_ressarcimentos TINYINT(1) NOT NULL DEFAULT 0
    AFTER acesso_pcpm;

CREATE TABLE pcpm_ressarcimentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ano SMALLINT NOT NULL,
    sequencial INT NOT NULL,
    numero VARCHAR(20) NOT NULL,
    centro_custos_id INT NOT NULL,
    equipamento_id INT NOT NULL,
    empresa_ocorrencia_id INT NOT NULL,
    ocorrencia_em DATETIME NOT NULL,
    descricao_ocorrencia TEXT NOT NULL,
    operador_id INT NULL,
    operador_nome_snapshot VARCHAR(150) NULL,
    operador_matricula_snapshot VARCHAR(50) NULL,
    funcionario_id INT NOT NULL,
    funcionario_nome_snapshot VARCHAR(150) NOT NULL,
    funcionario_matricula_snapshot VARCHAR(50) NULL,
    equipamento_snapshot VARCHAR(255) NOT NULL,
    empresa_ocorrencia_snapshot VARCHAR(150) NOT NULL,
    empresa_cliente_id INT NULL,
    empresa_cliente_snapshot VARCHAR(150) NULL,
    cliente_centro_custos VARCHAR(150) NULL,
    cliente_area VARCHAR(150) NULL,
    aprovador_email VARCHAR(150) NULL,
    aprovador_telefone VARCHAR(20) NULL,
    etapa_atual TINYINT NOT NULL DEFAULT 1,
    status_processo ENUM('Em andamento', 'Concluído', 'Cancelado') NOT NULL DEFAULT 'Em andamento',
    status_faturamento ENUM('Pendente', 'Realizado', 'Cancelado') NOT NULL DEFAULT 'Pendente',
    data_faturamento DATE NULL,
    cancelado_em DATETIME NULL,
    cancelado_por INT NULL,
    motivo_cancelamento TEXT NULL,
    reaberto_em DATETIME NULL,
    reaberto_por INT NULL,
    motivo_reabertura TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por INT NOT NULL,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    atualizado_por INT NOT NULL,
    UNIQUE KEY uq_pcpm_ressarcimentos_numero (numero),
    UNIQUE KEY uq_pcpm_ressarcimentos_sequencial (ano, sequencial),
    KEY idx_pcpm_ressarcimentos_centro_status (centro_custos_id, status_processo),
    KEY idx_pcpm_ressarcimentos_equipamento (equipamento_id),
    CONSTRAINT fk_ressarcimento_centro FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id),
    CONSTRAINT fk_ressarcimento_equipamento FOREIGN KEY (equipamento_id) REFERENCES pcpm_equipamentos(id),
    CONSTRAINT fk_ressarcimento_empresa_ocorrencia FOREIGN KEY (empresa_ocorrencia_id) REFERENCES pcpm_empresas(id),
    CONSTRAINT fk_ressarcimento_operador FOREIGN KEY (operador_id) REFERENCES pcpm_pessoas(id),
    CONSTRAINT fk_ressarcimento_funcionario FOREIGN KEY (funcionario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_ressarcimento_empresa_cliente FOREIGN KEY (empresa_cliente_id) REFERENCES pcpm_empresas(id),
    CONSTRAINT fk_ressarcimento_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_ressarcimento_atualizador FOREIGN KEY (atualizado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_ressarcimento_cancelador FOREIGN KEY (cancelado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_ressarcimento_reabertura FOREIGN KEY (reaberto_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pcpm_ressarcimentos_orcamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ressarcimento_id INT NOT NULL,
    versao INT NOT NULL,
    numero_orcamento_totvs VARCHAR(80) NOT NULL,
    valor_orcamento DECIMAL(15,2) NOT NULL,
    data_envio DATE NULL,
    status ENUM('Não enviado', 'Aguardando aprovação', 'Aprovado', 'Reprovado') NOT NULL DEFAULT 'Não enviado',
    vigente TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por INT NOT NULL,
    UNIQUE KEY uq_ressarcimento_orcamento_versao (ressarcimento_id, versao),
    CONSTRAINT fk_orcamento_ressarcimento FOREIGN KEY (ressarcimento_id) REFERENCES pcpm_ressarcimentos(id),
    CONSTRAINT fk_orcamento_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pcpm_ressarcimentos_anexos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ressarcimento_id INT NOT NULL,
    orcamento_id INT NULL,
    categoria ENUM('foto_avaria', 'checklist', 'orcamento', 'aprovacao_cliente', 'documentacao', 'outro') NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    caminho_arquivo VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por INT NOT NULL,
    KEY idx_ressarcimento_anexos (ressarcimento_id, categoria, ativo),
    CONSTRAINT fk_anexo_ressarcimento FOREIGN KEY (ressarcimento_id) REFERENCES pcpm_ressarcimentos(id),
    CONSTRAINT fk_anexo_orcamento FOREIGN KEY (orcamento_id) REFERENCES pcpm_ressarcimentos_orcamentos(id),
    CONSTRAINT fk_anexo_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pcpm_ressarcimentos_historico (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ressarcimento_id INT NOT NULL,
    etapa TINYINT NULL,
    evento VARCHAR(80) NOT NULL,
    descricao TEXT NOT NULL,
    dados_anteriores JSON NULL,
    dados_posteriores JSON NULL,
    usuario_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_ressarcimento_historico (ressarcimento_id, criado_em),
    CONSTRAINT fk_historico_ressarcimento FOREIGN KEY (ressarcimento_id) REFERENCES pcpm_ressarcimentos(id),
    CONSTRAINT fk_historico_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

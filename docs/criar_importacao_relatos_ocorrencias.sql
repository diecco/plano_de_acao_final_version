-- Importação de Relatos de Ocorrências exportados do Fluig.
-- Execute no schema de homologação antes de publicar a aplicação.

CREATE TABLE IF NOT EXISTS relatos_ocorrencias_importacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL,
    arquivo_hash CHAR(64) NOT NULL,
    usuario_id INT NOT NULL,
    total_linhas INT NOT NULL DEFAULT 0,
    inseridos INT NOT NULL DEFAULT 0,
    atualizados INT NOT NULL DEFAULT 0,
    inalterados INT NOT NULL DEFAULT 0,
    erros INT NOT NULL DEFAULT 0,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_rel_oc_importacoes_data (criado_em),
    CONSTRAINT fk_rel_oc_importacao_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS relatos_ocorrencias (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    solicitacao VARCHAR(40) NOT NULL,
    situacao_fluig VARCHAR(80) NULL,
    requisitante_identificador VARCHAR(100) NULL,
    requisitante_nome VARCHAR(180) NULL,
    localizacao_fluxo VARCHAR(255) NULL,
    responsavel_fluxo VARCHAR(180) NULL,
    inicio_em DATETIME NULL,
    fim_em DATETIME NULL,
    acao_tomada TEXT NULL,
    area_ocorrencia VARCHAR(180) NULL,
    centro_custos_id INT NULL,
    centro_custos_codigo VARCHAR(100) NULL,
    centro_custos_original VARCHAR(255) NULL,
    classificacao_ocorrencia VARCHAR(180) NULL,
    data_ocorrencia DATE NOT NULL,
    hora_ocorrencia TIME NULL,
    descricao_ocorrencia TEXT NOT NULL,
    local_ocorrencia VARCHAR(255) NULL,
    responsavel_registro VARCHAR(180) NULL,
    tipo_relato VARCHAR(180) NOT NULL,
    tipo_origem VARCHAR(100) NULL,
    turno VARCHAR(80) NULL,
    responsavel_turno VARCHAR(180) NULL,
    membros_atingidos TEXT NULL,
    dados_origem JSON NOT NULL,
    conteudo_hash CHAR(64) NOT NULL,
    importacao_id INT NOT NULL,
    importado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_rel_oc_solicitacao (solicitacao),
    KEY idx_rel_oc_data (data_ocorrencia),
    KEY idx_rel_oc_tipo (tipo_relato),
    KEY idx_rel_oc_cc (centro_custos_id),
    KEY idx_rel_oc_requisitante (requisitante_nome),
    CONSTRAINT fk_rel_oc_cc FOREIGN KEY (centro_custos_id)
        REFERENCES centros_custos (id),
    CONSTRAINT fk_rel_oc_importacao FOREIGN KEY (importacao_id)
        REFERENCES relatos_ocorrencias_importacoes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS relatos_ocorrencias_envolvidos (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    relato_id BIGINT NOT NULL,
    ordem SMALLINT NOT NULL DEFAULT 1,
    nome VARCHAR(180) NULL,
    matricula VARCHAR(100) NULL,
    email VARCHAR(180) NULL,
    centro_custos VARCHAR(255) NULL,
    descricao TEXT NULL,
    KEY idx_rel_oc_env_relato (relato_id),
    CONSTRAINT fk_rel_oc_env_relato FOREIGN KEY (relato_id)
        REFERENCES relatos_ocorrencias (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS relatos_ocorrencias_importacao_erros (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    importacao_id INT NOT NULL,
    linha INT NOT NULL,
    solicitacao VARCHAR(40) NULL,
    motivo VARCHAR(1000) NOT NULL,
    KEY idx_rel_oc_erro_importacao (importacao_id),
    CONSTRAINT fk_rel_oc_erro_importacao FOREIGN KEY (importacao_id)
        REFERENCES relatos_ocorrencias_importacoes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

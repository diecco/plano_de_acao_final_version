-- Estruturas de consulta para Observações Comportamentais importadas do Fluig.
CREATE TABLE IF NOT EXISTS oc_fluig_importacoes (
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
    KEY idx_oc_fluig_importacoes_data (criado_em),
    CONSTRAINT fk_oc_fluig_importacao_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_fluig_registros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    solicitacao VARCHAR(40) NOT NULL,
    data_observacao DATE NOT NULL,
    hora_observacao TIME NOT NULL DEFAULT '00:00:00',
    observador_nome VARCHAR(180) NOT NULL,
    observador_matricula VARCHAR(40) NULL,
    centro_custos_codigo VARCHAR(60) NULL,
    centro_custos_descricao VARCHAR(255) NULL,
    local_observado VARCHAR(255) NULL,
    setor_observado VARCHAR(255) NULL,
    area VARCHAR(100) NULL,
    atividade VARCHAR(255) NULL,
    pessoas_observadas INT NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'concluida',
    situacao_fluig VARCHAR(80) NULL,
    conteudo_hash CHAR(64) NOT NULL,
    importacao_id INT NOT NULL,
    importado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_oc_fluig_solicitacao (solicitacao),
    KEY idx_oc_fluig_data (data_observacao),
    KEY idx_oc_fluig_observador (observador_nome),
    CONSTRAINT fk_oc_fluig_registro_importacao FOREIGN KEY (importacao_id)
        REFERENCES oc_fluig_importacoes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_fluig_respostas (
    registro_id INT NOT NULL,
    item_codigo VARCHAR(15) NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    PRIMARY KEY (registro_id, item_codigo),
    CONSTRAINT fk_oc_fluig_resposta_registro FOREIGN KEY (registro_id)
        REFERENCES oc_fluig_registros (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Executar na base de HOMOLOGAÇÃO antes de publicar o módulo.

-- ADD COLUMN IF NOT EXISTS não é aceito por todas as versões do MySQL.
-- Esta verificação torna o comando compatível e permite reexecutar o arquivo.
SET @oc_coluna_existe = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'acesso_observacao_comportamental'
);

SET @oc_sql_coluna = IF(
    @oc_coluna_existe = 0,
    'ALTER TABLE usuarios ADD COLUMN acesso_observacao_comportamental TINYINT(1) NOT NULL DEFAULT 0',
    'SELECT ''A coluna acesso_observacao_comportamental já existe.'' AS informacao'
);

PREPARE oc_stmt_coluna FROM @oc_sql_coluna;
EXECUTE oc_stmt_coluna;
DEALLOCATE PREPARE oc_stmt_coluna;

CREATE TABLE IF NOT EXISTS oc_categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(5) NOT NULL,
    nome VARCHAR(150) NOT NULL,
    ordem INT NOT NULL DEFAULT 0,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uk_oc_categorias_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    categoria_id INT NOT NULL,
    codigo VARCHAR(15) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    ordem INT NOT NULL DEFAULT 0,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uk_oc_itens_codigo (codigo),
    KEY idx_oc_itens_categoria (categoria_id, ativo, ordem),
    CONSTRAINT fk_oc_item_categoria FOREIGN KEY (categoria_id)
        REFERENCES oc_categorias (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_registros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    centro_custos_id INT NOT NULL,
    observador_id INT NOT NULL,
    data_observacao DATE NOT NULL,
    hora_observacao TIME NOT NULL,
    local_observado VARCHAR(180) NOT NULL,
    setor_observado VARCHAR(180) NOT NULL,
    area VARCHAR(80) NOT NULL,
    atividade VARCHAR(255) NULL,
    pessoas_observadas INT NOT NULL DEFAULT 1,
    houve_abordagem TINYINT(1) NOT NULL DEFAULT 0,
    correcao_imediata TINYINT(1) NOT NULL DEFAULT 0,
    descricao_abordagem TEXT NULL,
    pontos_positivos TEXT NULL,
    observacoes_gerais TEXT NULL,
    status ENUM('rascunho', 'concluida', 'cancelada') NOT NULL DEFAULT 'rascunho',
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    concluido_em DATETIME NULL,
    cancelado_em DATETIME NULL,
    cancelado_por INT NULL,
    justificativa_cancelamento VARCHAR(500) NULL,
    excluido_em DATETIME NULL,
    excluido_por INT NULL,
    KEY idx_oc_registros_escopo_data (centro_custos_id, data_observacao),
    KEY idx_oc_registros_observador (observador_id),
    KEY idx_oc_registros_status (status),
    KEY idx_oc_registros_exclusao (excluido_em),
    CONSTRAINT fk_oc_registro_centro FOREIGN KEY (centro_custos_id)
        REFERENCES centros_custos (id),
    CONSTRAINT fk_oc_registro_observador FOREIGN KEY (observador_id)
        REFERENCES usuarios (id),
    CONSTRAINT fk_oc_registro_cancelado_por FOREIGN KEY (cancelado_por)
        REFERENCES usuarios (id),
    CONSTRAINT fk_oc_registro_excluido_por FOREIGN KEY (excluido_por)
        REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_respostas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    registro_id INT NOT NULL,
    item_id INT NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_oc_resposta_registro_item (registro_id, item_id),
    KEY idx_oc_respostas_item (item_id),
    CONSTRAINT fk_oc_resposta_registro FOREIGN KEY (registro_id)
        REFERENCES oc_registros (id) ON DELETE CASCADE,
    CONSTRAINT fk_oc_resposta_item FOREIGN KEY (item_id)
        REFERENCES oc_itens (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oc_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    registro_id INT NOT NULL,
    usuario_id INT NOT NULL,
    evento VARCHAR(80) NOT NULL,
    detalhes TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_oc_historico_registro (registro_id, criado_em),
    CONSTRAINT fk_oc_historico_registro FOREIGN KEY (registro_id)
        REFERENCES oc_registros (id) ON DELETE CASCADE,
    CONSTRAINT fk_oc_historico_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO oc_categorias (codigo, nome, ordem) VALUES
('A', 'Reação das pessoas', 1),
('B', 'Posição das pessoas', 2),
('C', 'Parte do corpo exposta', 3),
('D', 'Ferramentas e equipamentos', 4),
('E', 'Procedimentos', 5),
('F', 'Ordem, limpeza e organização', 6);

INSERT IGNORE INTO oc_itens (categoria_id, codigo, descricao, ordem)
SELECT c.id, dados.codigo, dados.descricao, dados.ordem
FROM oc_categorias c
JOIN (
    SELECT 'A' categoria, 'A01' codigo, 'Mudança de posição' descricao, 1 ordem UNION ALL
    SELECT 'A', 'A02', 'Parando o trabalho', 2 UNION ALL
    SELECT 'A', 'A03', 'Ajustando EPI', 3 UNION ALL
    SELECT 'A', 'A04', 'Adequando a tarefa', 4 UNION ALL
    SELECT 'A', 'A05', 'Correndo', 5 UNION ALL
    SELECT 'A', 'A06', 'Não usando o caminho seguro', 6 UNION ALL
    SELECT 'B', 'B01', 'Bater contra/ser atingido por', 1 UNION ALL
    SELECT 'B', 'B02', 'Ficar preso', 2 UNION ALL
    SELECT 'B', 'B03', 'Queda em diferentes níveis', 3 UNION ALL
    SELECT 'B', 'B04', 'Queda em mesmo nível', 4 UNION ALL
    SELECT 'B', 'B05', 'Queimadura', 5 UNION ALL
    SELECT 'B', 'B06', 'Choque elétrico', 6 UNION ALL
    SELECT 'B', 'B07', 'Inalar e/ou absorver contaminantes', 7 UNION ALL
    SELECT 'B', 'B08', 'Postura inadequada', 8 UNION ALL
    SELECT 'B', 'B09', 'Esforço excessivo', 9 UNION ALL
    SELECT 'C', 'C01', 'Cabeça', 1 UNION ALL
    SELECT 'C', 'C02', 'Sistema respiratório', 2 UNION ALL
    SELECT 'C', 'C03', 'Olhos', 3 UNION ALL
    SELECT 'C', 'C04', 'Face', 4 UNION ALL
    SELECT 'C', 'C05', 'Ouvidos', 5 UNION ALL
    SELECT 'C', 'C06', 'Mãos', 6 UNION ALL
    SELECT 'C', 'C07', 'Braços', 7 UNION ALL
    SELECT 'C', 'C08', 'Tronco', 8 UNION ALL
    SELECT 'C', 'C09', 'Pernas', 9 UNION ALL
    SELECT 'C', 'C10', 'Pés', 10 UNION ALL
    SELECT 'C', 'C11', 'Corpo inteiro', 11 UNION ALL
    SELECT 'D', 'D01', 'Impróprio para a tarefa', 1 UNION ALL
    SELECT 'D', 'D02', 'Utilizado incorretamente', 2 UNION ALL
    SELECT 'E', 'E01', 'Inexistente', 1 UNION ALL
    SELECT 'E', 'E02', 'Inadequado', 2 UNION ALL
    SELECT 'E', 'E03', 'Desconhecido', 3 UNION ALL
    SELECT 'E', 'E04', 'Não compreendido', 4 UNION ALL
    SELECT 'E', 'E05', 'Não seguido', 5 UNION ALL
    SELECT 'F', 'F01', 'Local sujo', 1 UNION ALL
    SELECT 'F', 'F02', 'Local desorganizado', 2 UNION ALL
    SELECT 'F', 'F03', 'Fora do padrão definido', 3
) dados ON dados.categoria = c.codigo;

-- Conceda a permissão somente aos usuários escolhidos, por exemplo:
-- UPDATE usuarios SET acesso_observacao_comportamental = 1 WHERE id = 4;

-- Execute no schema de homologacao antes de publicar o codigo.

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

INSERT INTO acr_metodologias (codigo, nome, implementada, ordem, ativo)
VALUES ('ishikawa', '6M (Ishikawa)', 1, 30, 1)
ON DUPLICATE KEY UPDATE
    nome = VALUES(nome),
    implementada = 1,
    ordem = VALUES(ordem),
    ativo = 1;

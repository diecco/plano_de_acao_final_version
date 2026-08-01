-- Execute no schema de homologacao antes de publicar o codigo.

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

INSERT INTO acr_metodologias (codigo, nome, implementada, ordem, ativo)
VALUES ('arvore_causas', 'Árvore de Causas', 1, 20, 1)
ON DUPLICATE KEY UPDATE
    nome = VALUES(nome),
    implementada = 1,
    ordem = VALUES(ordem),
    ativo = 1;

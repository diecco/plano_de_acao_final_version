-- Integra os checklists configuráveis ao Plano de Ação.
-- Execute no banco de homologação antes de testar respostas negativas com ação.

SET @checklist_origem_cc_sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'origens'
           AND COLUMN_NAME = 'centro_custos_id'
    ),
    'SELECT 1',
    'ALTER TABLE origens ADD COLUMN centro_custos_id INT NULL'
);
PREPARE checklist_origem_cc_stmt FROM @checklist_origem_cc_sql;
EXECUTE checklist_origem_cc_stmt;
DEALLOCATE PREPARE checklist_origem_cc_stmt;

CREATE TABLE IF NOT EXISTS checklist_execucao_acoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    execucao_id INT NOT NULL,
    item_chave VARCHAR(40) NOT NULL,
    acao_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_checklist_execucao_item_acao (execucao_id, item_chave),
    KEY idx_checklist_execucao_acoes_acao (acao_id),
    CONSTRAINT fk_checklist_execucao_acoes_execucao
        FOREIGN KEY (execucao_id) REFERENCES checklist_execucoes(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_checklist_execucao_acoes_acao
        FOREIGN KEY (acao_id) REFERENCES acoes(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

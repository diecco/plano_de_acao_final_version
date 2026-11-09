-- Integra checklists configuráveis ao agendamento SSMA.
-- Execute primeiro em homologação. O script pode ser reexecutado.

SET @schema_atual = DATABASE();

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = @schema_atual
           AND TABLE_NAME = 'agendamentos_ssma'
           AND COLUMN_NAME = 'checklist_modelo_id'
    ),
    'SELECT 1',
    'ALTER TABLE agendamentos_ssma ADD COLUMN checklist_modelo_id INT NULL AFTER procedimento_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.STATISTICS
         WHERE TABLE_SCHEMA = @schema_atual
           AND TABLE_NAME = 'agendamentos_ssma'
           AND INDEX_NAME = 'idx_agendamentos_checklist_modelo'
    ),
    'SELECT 1',
    'ALTER TABLE agendamentos_ssma ADD INDEX idx_agendamentos_checklist_modelo (checklist_modelo_id)'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
         WHERE CONSTRAINT_SCHEMA = @schema_atual
           AND TABLE_NAME = 'agendamentos_ssma'
           AND CONSTRAINT_NAME = 'fk_agendamentos_checklist_modelo'
    ),
    'SELECT 1',
    'ALTER TABLE agendamentos_ssma ADD CONSTRAINT fk_agendamentos_checklist_modelo FOREIGN KEY (checklist_modelo_id) REFERENCES checklist_modelos(id)'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = @schema_atual
           AND TABLE_NAME = 'checklist_execucoes'
           AND COLUMN_NAME = 'agendamento_id'
    ),
    'SELECT 1',
    'ALTER TABLE checklist_execucoes ADD COLUMN agendamento_id INT NULL AFTER centro_custos_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Uma execução só pode concluir um agendamento, e cada agendamento apenas uma vez.
SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.STATISTICS
         WHERE TABLE_SCHEMA = @schema_atual
           AND TABLE_NAME = 'checklist_execucoes'
           AND INDEX_NAME = 'uq_checklist_execucoes_agendamento'
    ),
    'SELECT 1',
    'ALTER TABLE checklist_execucoes ADD UNIQUE INDEX uq_checklist_execucoes_agendamento (agendamento_id)'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
         WHERE CONSTRAINT_SCHEMA = @schema_atual
           AND TABLE_NAME = 'checklist_execucoes'
           AND CONSTRAINT_NAME = 'fk_checklist_execucoes_agendamento'
    ),
    'SELECT 1',
    'ALTER TABLE checklist_execucoes ADD CONSTRAINT fk_checklist_execucoes_agendamento FOREIGN KEY (agendamento_id) REFERENCES agendamentos_ssma(id)'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT
    'Integração entre checklists configuráveis e agendamentos SSMA concluída.'
    AS resultado;

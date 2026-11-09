-- Separa a publicação do checklist de sua disponibilidade no agendamento SSMA.
-- Execute no banco de homologação antes de publicar a aplicação.

SET @schema_atual = DATABASE();

SET @sql = IF(
    EXISTS(
        SELECT 1
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = @schema_atual
           AND TABLE_NAME = 'checklist_modelos'
           AND COLUMN_NAME = 'disponivel_agendamento'
    ),
    'SELECT 1',
    'ALTER TABLE checklist_modelos ADD COLUMN disponivel_agendamento TINYINT(1) NOT NULL DEFAULT 0 AFTER exibir_menu'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT
    id,
    nome,
    status,
    ativo,
    exibir_menu,
    disponivel_agendamento
FROM checklist_modelos
ORDER BY nome;

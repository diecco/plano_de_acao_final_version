-- Evolução aditiva do primeiro esboço: definição dos itens de verificação.
SET @checklist_estrutura_existe = (
    SELECT COUNT(*)
      FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE()
       AND TABLE_NAME = 'checklist_modelos'
       AND COLUMN_NAME = 'estrutura_json'
);

SET @checklist_estrutura_sql = IF(
    @checklist_estrutura_existe = 0,
    'ALTER TABLE checklist_modelos ADD COLUMN estrutura_json JSON NULL AFTER descricao',
    'SELECT ''A coluna estrutura_json já existe.'' AS informacao'
);

PREPARE checklist_estrutura_stmt FROM @checklist_estrutura_sql;
EXECUTE checklist_estrutura_stmt;
DEALLOCATE PREPARE checklist_estrutura_stmt;

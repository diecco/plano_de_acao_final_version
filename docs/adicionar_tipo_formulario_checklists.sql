-- Evolui o construtor configurável para suportar checklists e formulários de SSMA.
-- Migração aditiva e reexecutável. Modelos existentes permanecem como checklist.

SET @tipo_fluxo_existe = (
    SELECT COUNT(*)
      FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE()
       AND TABLE_NAME = 'checklist_modelos'
       AND COLUMN_NAME = 'tipo_fluxo'
);

SET @tipo_fluxo_sql = IF(
    @tipo_fluxo_existe = 0,
    "ALTER TABLE checklist_modelos ADD COLUMN tipo_fluxo ENUM('checklist', 'formulario_ssma') NOT NULL DEFAULT 'checklist' AFTER descricao",
    'SELECT 1'
);

PREPARE tipo_fluxo_stmt FROM @tipo_fluxo_sql;
EXECUTE tipo_fluxo_stmt;
DEALLOCATE PREPARE tipo_fluxo_stmt;

UPDATE checklist_modelos
   SET tipo_fluxo = 'checklist'
 WHERE tipo_fluxo IS NULL OR tipo_fluxo = '';

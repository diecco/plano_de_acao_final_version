-- Atualização incremental para bancos que já receberam a estrutura inicial.
SET @sql_telefone_alternativo = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'recrutamento_candidatos'
              AND COLUMN_NAME = 'telefone_alternativo'
        ),
        'SELECT 1',
        'ALTER TABLE recrutamento_candidatos ADD COLUMN telefone_alternativo VARCHAR(30) NULL AFTER telefone'
    )
);
PREPARE stmt_telefone_alternativo FROM @sql_telefone_alternativo;
EXECUTE stmt_telefone_alternativo;
DEALLOCATE PREPARE stmt_telefone_alternativo;

-- Normaliza os telefones já cadastrados pela primeira versão do módulo.
UPDATE recrutamento_candidatos
SET telefone = REGEXP_REPLACE(telefone, '[^0-9]', '')
WHERE id >= 1
  AND telefone REGEXP '[^0-9]';

-- Compatibiliza a IFS do Cliente com os itens "Outros" da Revisão 13,
-- que não possuem potencial A, B ou C.
-- Idempotente: pode ser executado novamente.

ALTER TABLE ifs_cliente_respostas
    MODIFY COLUMN potencial CHAR(1) NULL;

ALTER TABLE ifs_cliente_desvios
    MODIFY COLUMN potencial CHAR(1) NULL;

SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('ifs_cliente_respostas', 'ifs_cliente_desvios')
  AND COLUMN_NAME = 'potencial'
ORDER BY TABLE_NAME;

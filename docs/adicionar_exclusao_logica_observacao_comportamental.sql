-- Executar na base de HOMOLOGAÇÃO antes de publicar esta alteração.
-- Compatível com versões do MySQL que não aceitam ADD COLUMN IF NOT EXISTS.

SET @oc_excluido_em_existe = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'oc_registros'
      AND COLUMN_NAME = 'excluido_em'
);
SET @oc_sql_excluido_em = IF(
    @oc_excluido_em_existe = 0,
    'ALTER TABLE oc_registros ADD COLUMN excluido_em DATETIME NULL',
    'SELECT ''A coluna excluido_em já existe.'' AS informacao'
);
PREPARE oc_stmt_excluido_em FROM @oc_sql_excluido_em;
EXECUTE oc_stmt_excluido_em;
DEALLOCATE PREPARE oc_stmt_excluido_em;

SET @oc_excluido_por_existe = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'oc_registros'
      AND COLUMN_NAME = 'excluido_por'
);
SET @oc_sql_excluido_por = IF(
    @oc_excluido_por_existe = 0,
    'ALTER TABLE oc_registros ADD COLUMN excluido_por INT NULL',
    'SELECT ''A coluna excluido_por já existe.'' AS informacao'
);
PREPARE oc_stmt_excluido_por FROM @oc_sql_excluido_por;
EXECUTE oc_stmt_excluido_por;
DEALLOCATE PREPARE oc_stmt_excluido_por;

SET @oc_indice_exclusao_existe = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'oc_registros'
      AND INDEX_NAME = 'idx_oc_registros_exclusao'
);
SET @oc_sql_indice_exclusao = IF(
    @oc_indice_exclusao_existe = 0,
    'ALTER TABLE oc_registros ADD KEY idx_oc_registros_exclusao (excluido_em)',
    'SELECT ''O índice de exclusão já existe.'' AS informacao'
);
PREPARE oc_stmt_indice_exclusao FROM @oc_sql_indice_exclusao;
EXECUTE oc_stmt_indice_exclusao;
DEALLOCATE PREPARE oc_stmt_indice_exclusao;

SET @oc_fk_excluido_por_existe = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'oc_registros'
      AND CONSTRAINT_NAME = 'fk_oc_registro_excluido_por'
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);
SET @oc_sql_fk_excluido_por = IF(
    @oc_fk_excluido_por_existe = 0,
    'ALTER TABLE oc_registros ADD CONSTRAINT fk_oc_registro_excluido_por FOREIGN KEY (excluido_por) REFERENCES usuarios (id)',
    'SELECT ''A chave de exclusão já existe.'' AS informacao'
);
PREPARE oc_stmt_fk_excluido_por FROM @oc_sql_fk_excluido_por;
EXECUTE oc_stmt_fk_excluido_por;
DEALLOCATE PREPARE oc_stmt_fk_excluido_por;

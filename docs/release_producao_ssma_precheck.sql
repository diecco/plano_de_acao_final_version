-- Execute em produção antes de qualquer migração e salve/exporte os resultados.
SELECT DATABASE() AS banco, NOW() AS verificado_em, @@version AS versao_mysql;

SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;

SELECT 'usuarios' tabela, COUNT(*) total FROM usuarios
UNION ALL SELECT 'acoes', COUNT(*) FROM acoes
UNION ALL SELECT 'hs_registros', COUNT(*) FROM hs_registros;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'usuarios'
  AND COLUMN_NAME IN (
      'acesso_ssma', 'acesso_observacao_comportamental',
      'acesso_desvios', 'pode_direcionar_desvios', 'gestor_ssma'
  )
ORDER BY ORDINAL_POSITION;

-- A consulta se adapta ao estágio atual do schema e não pressupõe que
-- pode_direcionar_desvios ou gestor_ssma já existam.
SET @precheck_tem_direcionador = EXISTS(
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'pode_direcionar_desvios'
);
SET @precheck_sql = IF(
    @precheck_tem_direcionador,
    'SELECT id, nome, matricula, acesso_ssma, pode_criar_agendamento_ssma, pode_direcionar_desvios FROM usuarios WHERE COALESCE(pode_criar_agendamento_ssma, 0) = 1 OR COALESCE(pode_direcionar_desvios, 0) = 1 ORDER BY nome',
    'SELECT id, nome, matricula, acesso_ssma, pode_criar_agendamento_ssma FROM usuarios WHERE COALESCE(pode_criar_agendamento_ssma, 0) = 1 ORDER BY nome'
);
PREPARE precheck_stmt FROM @precheck_sql;
EXECUTE precheck_stmt;
DEALLOCATE PREPARE precheck_stmt;

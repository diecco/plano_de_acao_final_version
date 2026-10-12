-- Execute depois das migrações e antes do deploy da aplicação.
SELECT DATABASE() AS banco, NOW() AS verificado_em;

SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'oc_categorias', 'oc_itens', 'oc_registros', 'oc_respostas',
      'oc_historico', 'desvios_categorias', 'desvios',
      'desvios_anexos', 'desvios_historico'
  )
ORDER BY TABLE_NAME;

SELECT 'usuarios' tabela, COUNT(*) total FROM usuarios
UNION ALL SELECT 'acoes', COUNT(*) FROM acoes
UNION ALL SELECT 'hs_registros', COUNT(*) FROM hs_registros;

SELECT
    (SELECT COUNT(*) FROM oc_categorias) AS categorias_oc,
    (SELECT COUNT(*) FROM oc_itens) AS itens_oc,
    (SELECT COUNT(*) FROM desvios_categorias) AS categorias_desvios;

SELECT id, nome, matricula, acesso_ssma, gestor_ssma,
       acesso_observacao_comportamental, acesso_desvios,
       pode_direcionar_desvios
FROM usuarios
WHERE COALESCE(acesso_ssma, 0) = 1
   OR COALESCE(gestor_ssma, 0) = 1
ORDER BY nome;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'oc_itens', 'oc_registros', 'oc_respostas', 'oc_historico',
      'desvios', 'desvios_anexos', 'desvios_historico'
  )
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

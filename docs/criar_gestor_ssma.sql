-- Migração aditiva e reexecutável.
SET @gestor_ssma_sql = IF(
    EXISTS(
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND COLUMN_NAME = 'gestor_ssma'
    ),
    'SELECT ''A coluna gestor_ssma já existe.'' AS informacao',
    'ALTER TABLE usuarios ADD COLUMN gestor_ssma TINYINT(1) NOT NULL DEFAULT 0'
);
PREPARE gestor_ssma_stmt FROM @gestor_ssma_sql;
EXECUTE gestor_ssma_stmt;
DEALLOCATE PREPARE gestor_ssma_stmt;

-- Conferência para definição manual dos novos Gestores SSMA.
SELECT
    id,
    nome,
    matricula,
    pode_criar_agendamento_ssma,
    pode_direcionar_desvios,
    gestor_ssma
FROM usuarios
WHERE ativo = 1
  AND (
      pode_criar_agendamento_ssma = 1
      OR pode_direcionar_desvios = 1
  )
ORDER BY nome;

-- Preserva e converte as autorizações operacionais já existentes.
UPDATE usuarios
SET gestor_ssma = 1,
    acesso_ssma = 1
WHERE id > 0
  AND (
      COALESCE(pode_criar_agendamento_ssma, 0) = 1
      OR COALESCE(pode_direcionar_desvios, 0) = 1
  );

-- Mantém os campos legados sincronizados enquanto ainda existirem no sistema.
UPDATE usuarios
SET acesso_observacao_comportamental = 1,
    acesso_desvios = 1
WHERE id > 0
  AND COALESCE(acesso_ssma, 0) = 1;

UPDATE usuarios
SET pode_direcionar_desvios = 1
WHERE id > 0
  AND COALESCE(gestor_ssma, 0) = 1;

-- Migração aditiva e reexecutável. Execute depois de criar_modulo_desvios.sql.
-- Nenhuma coluna ou registro existente é removido ou sobrescrito.

-- A ordem de execução é validada naturalmente pelos ALTER TABLE abaixo:
-- se a tabela não existir, a migração interrompe sem afetar as demais tabelas.

SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='matriz_exposicao'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN matriz_exposicao VARCHAR(20) NULL AFTER matriz_grave');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='matriz_controles'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN matriz_controles VARCHAR(20) NULL AFTER matriz_exposicao');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='matriz_ocorrencia'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN matriz_ocorrencia VARCHAR(20) NULL AFTER matriz_controles');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='probabilidade'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN probabilidade VARCHAR(10) NULL AFTER potencial');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='nivel_risco'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN nivel_risco VARCHAR(10) NULL AFTER probabilidade');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_utilizada'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_utilizada TINYINT(1) NOT NULL DEFAULT 0 AFTER nivel_risco');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_modelo'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_modelo VARCHAR(100) NULL AFTER ia_utilizada');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_descricao_original'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_descricao_original TEXT NULL AFTER ia_modelo');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_descricao_sugerida'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_descricao_sugerida TEXT NULL AFTER ia_descricao_original');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_severidade_sugerida'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_severidade_sugerida CHAR(1) NULL AFTER ia_descricao_sugerida');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_probabilidade_sugerida'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_probabilidade_sugerida VARCHAR(10) NULL AFTER ia_severidade_sugerida');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_justificativa'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_justificativa TEXT NULL AFTER ia_probabilidade_sugerida');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;
SET @desvio_sql = IF(EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='desvios' AND COLUMN_NAME='ia_confianca'), 'SELECT 1', 'ALTER TABLE desvios ADD COLUMN ia_confianca TINYINT UNSIGNED NULL AFTER ia_justificativa');
PREPARE desvio_stmt FROM @desvio_sql; EXECUTE desvio_stmt; DEALLOCATE PREPARE desvio_stmt;

-- Registros anteriores permanecem válidos; a nova matriz é exigida somente nos novos relatos.

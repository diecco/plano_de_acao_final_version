-- Completa o cabeçalho da IFS do Cliente conforme o formulário Rev13.
-- Pode ser executado novamente: somente colunas ausentes serão criadas.

DROP PROCEDURE IF EXISTS atualizar_cabecalho_ifs_cliente_rev13;
DELIMITER $$
CREATE PROCEDURE atualizar_cabecalho_ifs_cliente_rev13()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ifs_cliente_inspecoes'
          AND COLUMN_NAME = 'gerencia'
    ) THEN
        ALTER TABLE ifs_cliente_inspecoes
            ADD COLUMN gerencia VARCHAR(255) NULL AFTER referencia_cliente;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ifs_cliente_inspecoes'
          AND COLUMN_NAME = 'administrador_contrato'
    ) THEN
        ALTER TABLE ifs_cliente_inspecoes
            ADD COLUMN administrador_contrato VARCHAR(255) NULL AFTER gerencia;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ifs_cliente_inspecoes'
          AND COLUMN_NAME = 'contratada'
    ) THEN
        ALTER TABLE ifs_cliente_inspecoes
            ADD COLUMN contratada VARCHAR(255) NULL AFTER administrador_contrato;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ifs_cliente_inspecoes'
          AND COLUMN_NAME = 'profissional_sesmt_contratada_lideranca'
    ) THEN
        ALTER TABLE ifs_cliente_inspecoes
            ADD COLUMN profissional_sesmt_contratada_lideranca VARCHAR(255) NULL AFTER contratada;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ifs_cliente_inspecoes'
          AND COLUMN_NAME = 'sesmt_gerdau_fiscalizadora'
    ) THEN
        ALTER TABLE ifs_cliente_inspecoes
            ADD COLUMN sesmt_gerdau_fiscalizadora VARCHAR(255) NULL AFTER profissional_sesmt_contratada_lideranca;
    END IF;
END$$
DELIMITER ;

CALL atualizar_cabecalho_ifs_cliente_rev13();
DROP PROCEDURE IF EXISTS atualizar_cabecalho_ifs_cliente_rev13;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ifs_cliente_inspecoes'
  AND COLUMN_NAME IN (
      'gerencia',
      'administrador_contrato',
      'contratada',
      'profissional_sesmt_contratada_lideranca',
      'sesmt_gerdau_fiscalizadora'
  )
ORDER BY ORDINAL_POSITION;

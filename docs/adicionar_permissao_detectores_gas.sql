-- Execute uma única vez no schema de homologação antes do deploy.
-- Administradores continuam com acesso automático, independentemente da flag.

ALTER TABLE usuarios
    ADD COLUMN acesso_detectores_gas TINYINT(1) NOT NULL DEFAULT 0
    AFTER acesso_pcpm;

-- Verificação:
SHOW COLUMNS FROM usuarios LIKE 'acesso_detectores_gas';

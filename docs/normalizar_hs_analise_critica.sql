-- Execute primeiro no schema de homologação.
-- Preserva o campo hs_registros.participantes durante a transição.

ALTER TABLE hs_registros
    ADD COLUMN centro_custos_id INT NULL AFTER id_auditor;

UPDATE hs_registros r
JOIN usuarios u ON u.id = r.id_auditor
SET r.centro_custos_id = u.centro_custos_id
WHERE r.centro_custos_id IS NULL;

ALTER TABLE hs_registros
    ADD INDEX idx_hs_registros_centro_data (centro_custos_id, data),
    ADD CONSTRAINT fk_hs_registros_centro
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id);

CREATE TABLE hs_registros_participantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_registro INT NOT NULL,
    usuario_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hs_registro_participante (id_registro, usuario_id),
    INDEX idx_hs_participante_usuario (usuario_id, id_registro),
    CONSTRAINT fk_hs_participante_registro
        FOREIGN KEY (id_registro) REFERENCES hs_registros(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_hs_participante_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Migra os IDs numéricos armazenados no campo CSV legado.
INSERT IGNORE INTO hs_registros_participantes (id_registro, usuario_id)
SELECT r.id, CAST(j.usuario_id AS UNSIGNED)
FROM hs_registros r
JOIN JSON_TABLE(
    CONCAT(
        '["',
        REPLACE(
            TRIM(BOTH ',' FROM REPLACE(r.participantes, ' ', '')),
            ',',
            '","'
        ),
        '"]'
    ),
    '$[*]' COLUMNS (usuario_id VARCHAR(30) PATH '$')
) AS j
JOIN usuarios u ON u.id = CAST(j.usuario_id AS UNSIGNED)
WHERE r.participantes IS NOT NULL
  AND TRIM(r.participantes) <> '';

SELECT
    (SELECT COUNT(*) FROM hs_registros) AS total_hs,
    (SELECT COUNT(DISTINCT id_registro) FROM hs_registros_participantes)
        AS hs_com_participantes_normalizados,
    (SELECT COUNT(*) FROM hs_registros_participantes) AS participacoes_migradas;

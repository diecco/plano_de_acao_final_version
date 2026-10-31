-- Executar primeiro em homologação.
-- A relação histórica permanece intacta e passa a representar os AUDITADOS.
-- A nova tabela armazena somente participantes/acompanhantes da realização.

CREATE TABLE IF NOT EXISTS hs_registros_acompanhantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_registro INT NOT NULL,
    usuario_id INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hs_registro_acompanhante (id_registro, usuario_id),
    INDEX idx_hs_acompanhante_usuario (usuario_id, id_registro),
    CONSTRAINT fk_hs_acompanhante_registro
        FOREIGN KEY (id_registro) REFERENCES hs_registros(id) ON DELETE CASCADE,
    CONSTRAINT fk_hs_acompanhante_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

SELECT
    (SELECT COUNT(*) FROM hs_registros) AS total_hs,
    (SELECT COUNT(DISTINCT id_registro) FROM hs_registros_participantes)
        AS hs_com_auditados,
    (SELECT COUNT(*) FROM hs_registros_participantes) AS auditados_preservados,
    (SELECT COUNT(*) FROM hs_registros_acompanhantes) AS novos_participantes;


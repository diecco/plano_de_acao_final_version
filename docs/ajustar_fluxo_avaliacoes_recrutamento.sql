-- Execute uma única vez no schema de homologação.
-- Preserva as candidaturas e etapas já cadastradas.

ALTER TABLE recrutamento_candidaturas
    ADD COLUMN decisao_resultado ENUM(
        'aprovado', 'aprovado_restricao', 'reprovado', 'stand_by'
    ) NULL AFTER status,
    ADD COLUMN decisao_parecer TEXT NULL AFTER decisao_resultado,
    ADD COLUMN decisao_por INT NULL AFTER decisao_parecer,
    ADD COLUMN decisao_em DATETIME NULL AFTER decisao_por,
    ADD CONSTRAINT fk_recrutamento_candidatura_decisao_por
        FOREIGN KEY (decisao_por) REFERENCES usuarios(id) ON DELETE SET NULL;

CREATE TABLE recrutamento_pareceres_complementares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    etapa_id INT NOT NULL,
    parecer TEXT NOT NULL,
    autor_id INT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recrutamento_complemento_etapa
        FOREIGN KEY (etapa_id) REFERENCES recrutamento_etapas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_complemento_autor
        FOREIGN KEY (autor_id) REFERENCES usuarios(id),
    INDEX idx_recrutamento_complemento_etapa (etapa_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

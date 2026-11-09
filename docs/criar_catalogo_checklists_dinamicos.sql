-- Primeiro esboço do catálogo de checklists configuráveis do TrackPlan.
-- Migração aditiva e reexecutável para homologação.

CREATE TABLE IF NOT EXISTS checklist_modelos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT NULL,
    abrangencia ENUM('global', 'centros') NOT NULL DEFAULT 'global',
    status ENUM('rascunho', 'publicado') NOT NULL DEFAULT 'rascunho',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    exibir_menu TINYINT(1) NOT NULL DEFAULT 1,
    disponivel_agendamento TINYINT(1) NOT NULL DEFAULT 0,
    modulo_menu ENUM('ssma', 'gestao_ssma') NOT NULL DEFAULT 'ssma',
    ordem_menu INT NOT NULL DEFAULT 0,
    criado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    publicado_em TIMESTAMP NULL,
    CONSTRAINT fk_checklist_modelo_criador
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    UNIQUE KEY uq_checklist_modelo_nome (nome),
    INDEX ix_checklist_modelo_menu (
        ativo, status, exibir_menu, modulo_menu, ordem_menu
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS checklist_modelos_centros (
    checklist_id INT NOT NULL,
    centro_custos_id INT NOT NULL,
    PRIMARY KEY (checklist_id, centro_custos_id),
    CONSTRAINT fk_checklist_modelo_centro_checklist
        FOREIGN KEY (checklist_id) REFERENCES checklist_modelos(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_checklist_modelo_centro_custos
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

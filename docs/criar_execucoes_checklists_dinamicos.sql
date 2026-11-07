-- Estrutura de preenchimentos dos checklists configuráveis.
-- Execute no banco de homologação trackplan_teste.

CREATE TABLE IF NOT EXISTS checklist_execucoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checklist_id INT NOT NULL,
    executor_id INT NOT NULL,
    centro_custos_id INT NULL,
    status ENUM('concluido') NOT NULL DEFAULT 'concluido',
    respostas_json JSON NOT NULL,
    estrutura_snapshot_json JSON NOT NULL,
    observacoes TEXT NULL,
    concluido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_checklist_execucoes_modelo_data (checklist_id, concluido_em),
    INDEX idx_checklist_execucoes_executor (executor_id),
    INDEX idx_checklist_execucoes_centro (centro_custos_id),
    CONSTRAINT fk_checklist_execucoes_modelo
        FOREIGN KEY (checklist_id) REFERENCES checklist_modelos(id),
    CONSTRAINT fk_checklist_execucoes_executor
        FOREIGN KEY (executor_id) REFERENCES usuarios(id),
    CONSTRAINT fk_checklist_execucoes_centro
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

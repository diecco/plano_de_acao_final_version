CREATE TABLE IF NOT EXISTS comunicados_visuais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_interno VARCHAR(150) NOT NULL,
    imagem VARCHAR(255) NOT NULL,
    corporativo TINYINT(1) NOT NULL DEFAULT 0,
    data_inicio DATE NULL,
    data_fim DATE NULL,
    ordem INT NOT NULL DEFAULT 0,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_comunicado_visual_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_comunicado_visual_vigencia (ativo, data_inicio, data_fim),
    INDEX idx_comunicado_visual_ordem (ordem)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS comunicados_visuais_centros (
    comunicado_id INT NOT NULL,
    centro_custos_id INT NOT NULL,
    PRIMARY KEY (comunicado_id, centro_custos_id),
    CONSTRAINT fk_comunicado_visual_centro_comunicado
        FOREIGN KEY (comunicado_id) REFERENCES comunicados_visuais(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_comunicado_visual_centro_cc
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_comunicado_visual_centro_cc (centro_custos_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

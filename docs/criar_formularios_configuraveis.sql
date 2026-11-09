CREATE TABLE IF NOT EXISTS formulario_modelos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT NULL,
    abrangencia ENUM('global', 'centros') NOT NULL DEFAULT 'global',
    status ENUM('rascunho', 'publicado') NOT NULL DEFAULT 'rascunho',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    estrutura_json JSON NULL,
    criado_por INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_formulario_modelo_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS formulario_modelos_centros (
    modelo_id INT NOT NULL,
    centro_custos_id INT NOT NULL,
    PRIMARY KEY (modelo_id, centro_custos_id),
    CONSTRAINT fk_formulario_modelo_centro_modelo FOREIGN KEY (modelo_id) REFERENCES formulario_modelos(id) ON DELETE CASCADE,
    CONSTRAINT fk_formulario_modelo_centro_centro FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
);

CREATE TABLE IF NOT EXISTS formulario_registros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    modelo_id INT NOT NULL,
    respostas_json JSON NOT NULL,
    centro_custos_id INT NULL,
    criado_por INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_formulario_registro_modelo FOREIGN KEY (modelo_id) REFERENCES formulario_modelos(id),
    CONSTRAINT fk_formulario_registro_centro FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id),
    CONSTRAINT fk_formulario_registro_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id),
    INDEX idx_formulario_registros_modelo_data (modelo_id, criado_em),
    INDEX idx_formulario_registros_centro (centro_custos_id)
);

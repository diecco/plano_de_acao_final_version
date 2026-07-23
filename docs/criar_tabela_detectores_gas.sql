CREATE TABLE IF NOT EXISTS detectores_gas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patrimonio VARCHAR(9) NOT NULL UNIQUE,
    fabricante VARCHAR(120) NOT NULL,
    marca VARCHAR(120) NOT NULL,
    modelo VARCHAR(120) NOT NULL,
    data_calibracao DATE NULL,
    validade_calibracao DATE NULL,
    centro_custos_id INT NOT NULL,
    status_operacional VARCHAR(30) NOT NULL DEFAULT 'disponivel',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por INT NULL,
    atualizado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_detectores_gas_cc
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_detectores_gas_criado_por
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_detectores_gas_atualizado_por
        FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_detectores_gas_status
        CHECK (
            status_operacional IN (
                'disponivel',
                'em_uso',
                'em_calibracao',
                'com_defeito'
            )
        ),
    CONSTRAINT chk_detectores_gas_calibracao
        CHECK (
            validade_calibracao IS NULL
            OR data_calibracao IS NULL
            OR validade_calibracao >= data_calibracao
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

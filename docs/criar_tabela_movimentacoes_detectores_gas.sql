CREATE TABLE IF NOT EXISTS detectores_gas_movimentacoes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    detector_id INT NOT NULL,
    entregue_por_id INT NOT NULL,
    retirado_por_id INT NOT NULL,
    recebido_por_id INT NULL,
    devolvido_por_id INT NULL,
    rfid_entrega_responsavel VARCHAR(120) NOT NULL,
    rfid_retirante VARCHAR(120) NOT NULL,
    rfid_recebimento_responsavel VARCHAR(120) NULL,
    rfid_devolvente VARCHAR(120) NULL,
    retirado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    devolvido_em TIMESTAMP NULL,
    condicao_devolucao VARCHAR(30) NULL,
    origem_defeito VARCHAR(30) NULL,
    observacao_devolucao TEXT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_detector_movimentacao_aberta (detector_id, devolvido_em),
    INDEX idx_detector_retirado_por (retirado_por_id, retirado_em),
    CONSTRAINT fk_detector_mov_detector
        FOREIGN KEY (detector_id) REFERENCES detectores_gas(id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_detector_mov_entregue_por
        FOREIGN KEY (entregue_por_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_detector_mov_retirado_por
        FOREIGN KEY (retirado_por_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_detector_mov_recebido_por
        FOREIGN KEY (recebido_por_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE,
    CONSTRAINT fk_detector_mov_devolvido_por
        FOREIGN KEY (devolvido_por_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE,
    CONSTRAINT chk_detector_mov_condicao
        CHECK (
            condicao_devolucao IS NULL
            OR condicao_devolucao IN (
                'perfeitas_condicoes',
                'com_defeito'
            )
        ),
    CONSTRAINT chk_detector_mov_origem_defeito
        CHECK (
            origem_defeito IS NULL
            OR origem_defeito IN (
                'mau_uso',
                'desgaste_normal'
            )
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

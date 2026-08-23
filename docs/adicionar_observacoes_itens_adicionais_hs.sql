-- Execute no schema de homologacao antes de publicar o codigo.

ALTER TABLE hs_registros
    ADD COLUMN observacoes_gerais TEXT NULL AFTER participantes;

CREATE TABLE hs_registros_adicionais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_registro INT NOT NULL,
    tipo ENUM('desvio', 'melhoria', 'oportunidade', 'outro') NOT NULL,
    item_verificacao VARCHAR(500) NOT NULL,
    descricao_situacao TEXT NOT NULL,
    descricao_acao TEXT NULL,
    prazo DATE NULL,
    id_acao_gerada INT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_hs_adicionais_registro (id_registro),
    INDEX idx_hs_adicionais_acao (id_acao_gerada),
    CONSTRAINT fk_hs_adicionais_registro
        FOREIGN KEY (id_registro) REFERENCES hs_registros(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_hs_adicionais_acao
        FOREIGN KEY (id_acao_gerada) REFERENCES acoes(id)
        ON DELETE SET NULL
);

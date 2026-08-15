-- Validação externa para mobilização do candidato no cliente.
-- Não armazena antecedentes, processos ou justificativas sensíveis.

CREATE TABLE IF NOT EXISTS recrutamento_validacoes_cliente (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidatura_id INT NOT NULL,
    cliente VARCHAR(160) NOT NULL,
    unidade VARCHAR(160) NULL,
    sistema_externo VARCHAR(120) NULL,
    documento_identidade VARCHAR(40) NOT NULL,
    obrigatoria TINYINT(1) NOT NULL DEFAULT 1,
    status ENUM(
        'aguardando_envio', 'em_analise', 'complementacao',
        'aprovado', 'reprovado', 'cancelado'
    ) NOT NULL DEFAULT 'aguardando_envio',
    protocolo VARCHAR(100) NULL,
    data_solicitacao DATE NULL,
    data_resposta DATE NULL,
    validade_aprovacao DATE NULL,
    motivo_categoria ENUM(
        'restricao_cliente', 'divergencia_documental',
        'informacoes_insuficientes', 'criterio_interno_cliente', 'outro'
    ) NULL,
    observacao_operacional TEXT NULL,
    evidencia_arquivo VARCHAR(255) NULL,
    criado_por INT NOT NULL,
    atualizado_por INT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_recrutamento_validacao_candidatura
        FOREIGN KEY (candidatura_id) REFERENCES recrutamento_candidaturas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recrutamento_validacao_criado
        FOREIGN KEY (criado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_recrutamento_validacao_atualizado
        FOREIGN KEY (atualizado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_recrutamento_validacao_candidatura (candidatura_id),
    INDEX idx_recrutamento_validacao_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

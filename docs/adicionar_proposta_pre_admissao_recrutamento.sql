-- Implementa proposta simplificada e pré-admissão no recrutamento.
-- Execute uma única vez no schema de homologação antes do deploy.

ALTER TABLE recrutamento_propostas
    MODIFY COLUMN cargo VARCHAR(160) NULL,
    MODIFY COLUMN salario DECIMAL(12,2) NULL,
    MODIFY COLUMN status ENUM(
        'elaboracao', 'enviada', 'aceita', 'recusada', 'expirada',
        'negociacao', 'nao_enviada', 'rejeitada', 'sem_retorno'
    ) NOT NULL DEFAULT 'nao_enviada';

UPDATE recrutamento_propostas
SET status = CASE
    WHEN status = 'elaboracao' THEN 'nao_enviada'
    WHEN status = 'recusada' THEN 'rejeitada'
    WHEN status IN ('expirada', 'negociacao') THEN 'sem_retorno'
    ELSE status
END
WHERE id > 0;

ALTER TABLE recrutamento_propostas
    MODIFY COLUMN status ENUM(
        'nao_enviada', 'enviada', 'aceita', 'rejeitada', 'sem_retorno'
    ) NOT NULL DEFAULT 'nao_enviada';

ALTER TABLE recrutamento_pre_admissao
    MODIFY COLUMN aso_status ENUM(
        'aguardando_agendamento', 'agendado', 'aguardando_resultado',
        'apto', 'inapto', 'avaliacao_complementar',
        'concluido', 'cancelado'
    ) NOT NULL DEFAULT 'aguardando_agendamento',
    ADD COLUMN aso_resultado ENUM('apto', 'inapto', 'apto_restricao') NULL
        AFTER aso_data_prevista;

UPDATE recrutamento_pre_admissao
SET aso_resultado = CASE
        WHEN aso_status = 'apto' THEN 'apto'
        WHEN aso_status = 'inapto' THEN 'inapto'
        WHEN aso_status = 'avaliacao_complementar' THEN 'apto_restricao'
        ELSE aso_resultado
    END,
    aso_status = CASE
        WHEN aso_status IN ('apto', 'inapto', 'avaliacao_complementar')
            THEN 'concluido'
        ELSE aso_status
    END
WHERE id > 0;

ALTER TABLE recrutamento_pre_admissao
    MODIFY COLUMN aso_status ENUM(
        'aguardando_agendamento', 'agendado', 'aguardando_resultado',
        'concluido', 'cancelado'
    ) NOT NULL DEFAULT 'aguardando_agendamento';

ALTER TABLE recrutamento_documentos_candidatura
    MODIFY COLUMN status ENUM(
        'solicitado', 'recebido', 'conferido', 'correcao', 'dispensado',
        'pendente', 'nao_aplicavel', 'inconsistente'
    ) NOT NULL DEFAULT 'pendente';

UPDATE recrutamento_documentos_candidatura
SET status = CASE
    WHEN status IN ('solicitado', 'correcao') THEN 'pendente'
    WHEN status = 'conferido' THEN 'recebido'
    WHEN status = 'dispensado' THEN 'nao_aplicavel'
    ELSE status
END
WHERE id > 0;

ALTER TABLE recrutamento_documentos_candidatura
    MODIFY COLUMN status ENUM(
        'pendente', 'recebido', 'nao_aplicavel', 'inconsistente'
    ) NOT NULL DEFAULT 'pendente';

INSERT IGNORE INTO recrutamento_tipos_documento (nome, ativo) VALUES
    ('Documento de identidade', 1),
    ('CPF', 1),
    ('Comprovante de residência', 1),
    ('Carteira de trabalho', 1),
    ('CNH', 1),
    ('Certificado de reservista', 1),
    ('Cartão de vacinação', 1),
    ('Certidão de nascimento ou casamento', 1),
    ('Certidão de nascimento dos filhos', 1);

ALTER TABLE recrutamento_ciclos_historico
    ADD COLUMN proposta_status VARCHAR(30) NULL AFTER pre_cadastro_observacao,
    ADD COLUMN proposta_enviada_em DATETIME NULL AFTER proposta_status,
    ADD COLUMN aso_status VARCHAR(30) NULL AFTER proposta_enviada_em,
    ADD COLUMN aso_resultado VARCHAR(30) NULL AFTER aso_status,
    ADD COLUMN aso_data_prevista DATE NULL AFTER aso_resultado,
    ADD COLUMN documentos_status VARCHAR(30) NULL AFTER aso_data_prevista;

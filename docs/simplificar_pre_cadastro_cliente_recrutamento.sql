-- Simplifica a validação do cliente para uma etapa direta do processo seletivo.
-- Execute uma única vez no schema de homologação antes de testar esta versão.

ALTER TABLE recrutamento_validacoes_cliente
    MODIFY COLUMN status ENUM(
        'aguardando_envio',
        'em_analise',
        'complementacao',
        'aprovado',
        'reprovado',
        'cancelado',
        'nao_iniciado',
        'aguardando_validacao'
    ) NOT NULL DEFAULT 'nao_iniciado';

UPDATE recrutamento_validacoes_cliente
SET status = CASE
    WHEN status IN ('em_analise', 'complementacao') THEN 'aguardando_validacao'
    WHEN status IN ('aguardando_envio', 'cancelado') THEN 'nao_iniciado'
    ELSE status
END
WHERE id > 0;

ALTER TABLE recrutamento_validacoes_cliente
    MODIFY COLUMN status ENUM(
        'nao_iniciado',
        'aguardando_validacao',
        'aprovado',
        'reprovado'
    ) NOT NULL DEFAULT 'nao_iniciado';

ALTER TABLE recrutamento_ciclos_historico
    ADD COLUMN pre_cadastro_cliente VARCHAR(160) NULL AFTER arquivado_por,
    ADD COLUMN pre_cadastro_status VARCHAR(30) NULL AFTER pre_cadastro_cliente,
    ADD COLUMN pre_cadastro_observacao TEXT NULL AFTER pre_cadastro_status;

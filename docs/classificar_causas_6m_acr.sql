-- Execute no schema de homologacao depois de adicionar_metodologia_6m_acr.sql.
-- O MySQL utilizado nao aceita ADD COLUMN IF NOT EXISTS; execute uma unica vez.

ALTER TABLE acr_6m_itens
    ADD COLUMN classificacao VARCHAR(20) NOT NULL DEFAULT 'potencial'
        AFTER causa_raiz,
    ADD COLUMN justificativa TEXT NULL AFTER classificacao,
    ADD COLUMN validacao TEXT NULL AFTER justificativa,
    ADD CONSTRAINT chk_acr_6m_classificacao CHECK (classificacao IN (
        'potencial', 'descartada', 'contribuinte', 'basica', 'fundamental'
    ));

-- TrackPlan - amplia o campo de pergunta da metodologia 5 Porquês
-- Executar no schema de homologação antes de publicar a interface atualizada.

SELECT DATABASE() AS banco_em_uso;

ALTER TABLE acr_5_porques
    MODIFY COLUMN pergunta VARCHAR(500) NOT NULL;

SHOW COLUMNS FROM acr_5_porques LIKE 'pergunta';

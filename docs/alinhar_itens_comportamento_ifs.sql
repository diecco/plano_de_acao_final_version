-- Alinha o bloco 25 - COMPORTAMENTO ao formulario IFS TRADIMAQ NOV/2026.
-- Execute no schema de homologacao. Itens excedentes sao inativados, nao excluidos.

START TRANSACTION;

SET @bloco_comportamento_id = (
    SELECT id FROM ifs_blocos
    WHERE UPPER(TRIM(nome)) LIKE '%COMPORTAMENTO%'
    ORDER BY ativo DESC, ordem, id LIMIT 1
);

SET @sql_validacao = IF(
    @bloco_comportamento_id IS NULL,
    'SIGNAL SQLSTATE ''45000'' SET MESSAGE_TEXT = ''Bloco COMPORTAMENTO nao encontrado em ifs_blocos''',
    'DO 0'
);
PREPARE stmt_validacao FROM @sql_validacao;
EXECUTE stmt_validacao;
DEALLOCATE PREPARE stmt_validacao;

UPDATE ifs_itens
SET descricao = CASE codigo
        WHEN '25.1' THEN 'Colaborador tem olhos na atividade, sem pressa, com equilíbrio, tração e firmeza, manteve posição ao ser observado e adequada a execução da atividade?'
        WHEN '25.2' THEN 'Colaborador utiliza os EPI''s previstos para atividade de forma correta?'
        WHEN '25.3' THEN 'O colaborador está posicionado de forma correta sem os riscos de: colisões ou impactos, prensamento, quedas (sejam no mesmo nível ou em níveis diferentes), queimaduras, choques elétricos, e exposição a contaminantes (por inalação, absorção ou ingestão)?'
        WHEN '25.4' THEN 'Colaborador utiliza ferramenta de forma correta sem improviso? E estas estão em condições seguras para uso?'
        WHEN '25.5' THEN 'Os colaboradores atendem a proibição quanto ao porte de ferramentas que possuem gume ou ponta em bolsos?'
        WHEN '25.6' THEN 'Colaborador cumpre os Procedimentos, OS, APR e PT?'
        WHEN '25.7' THEN 'O colaborador demonstra aplicação dos 5S?'
        WHEN '25.8' THEN 'Está sendo cumprida a proibição de utilizar adornos como: brincos, pulseiras, relógios, cordões, anéis, etc?'
        WHEN '25.9' THEN 'Todos os colaboradores das frentes de serviços, próximas às áreas operacionais, conhecem os riscos específicos a que estão expostos. (Entrevista)'
        WHEN '25.10' THEN 'É seguido a proibição de não fumar em locais de riscos ou que não estejam designados para uso de cigarro?'
        WHEN '25.11' THEN 'É atendida a regra de não utilizar o celular em área operacional ou portar durante a condução e operação de Equipamentos Móveis, Ponte Rolante e em Áreas Classificadas?'
        WHEN '25.12' THEN 'É atendida a proibição de uso de barba ao usar máscara?'
        WHEN '25.13' THEN 'Foi aberta Recusa Tarefa para condições físicas ou sistêmicas na área de atuação/atendimento passivas de serem identificadas e paralisada a execução?'
        WHEN '25.14' THEN 'Outros*'
    END,
    potencial = CASE codigo
        WHEN '25.1' THEN 'B' WHEN '25.2' THEN 'A' WHEN '25.3' THEN 'A'
        WHEN '25.4' THEN 'A' WHEN '25.5' THEN 'B' WHEN '25.6' THEN 'A'
        WHEN '25.7' THEN 'B' WHEN '25.8' THEN 'B' WHEN '25.9' THEN 'A'
        WHEN '25.10' THEN 'B' WHEN '25.11' THEN 'A' WHEN '25.12' THEN 'B'
        WHEN '25.13' THEN 'A' WHEN '25.14' THEN 'C'
    END,
    ordem = CAST(SUBSTRING_INDEX(codigo, '.', -1) AS UNSIGNED),
    ativo = 1
WHERE bloco_id = @bloco_comportamento_id
  AND codigo IN (
      '25.1', '25.2', '25.3', '25.4', '25.5', '25.6', '25.7',
      '25.8', '25.9', '25.10', '25.11', '25.12', '25.13', '25.14'
  );

-- Preserva eventuais respostas antigas ligadas aos itens 25.15 e 25.16.
UPDATE ifs_itens
SET ativo = 0
WHERE bloco_id = @bloco_comportamento_id
  AND codigo NOT IN (
      '25.1', '25.2', '25.3', '25.4', '25.5', '25.6', '25.7',
      '25.8', '25.9', '25.10', '25.11', '25.12', '25.13', '25.14'
  );

COMMIT;

SELECT COUNT(*) AS total_itens_ativos
FROM ifs_itens
WHERE bloco_id = @bloco_comportamento_id AND ativo = 1;

SELECT codigo, descricao, potencial, ordem, ativo
FROM ifs_itens
WHERE bloco_id = @bloco_comportamento_id
ORDER BY ativo DESC, ordem, id;

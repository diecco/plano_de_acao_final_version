-- Atualiza integralmente o catalogo da IFS para a Revisao 13 (abril/2026).
-- A revisao anterior permanece inativa para preservar o historico das inspecoes.
-- Fonte: 01_Anexo VI - Formulario de Inspecao Frente de Servicos Rev13.

CREATE TABLE IF NOT EXISTS ifs_catalogo_versoes (
    versao VARCHAR(30) PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    aplicado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP PROCEDURE IF EXISTS aplicar_catalogo_ifs_rev13;
DELIMITER $$
CREATE PROCEDURE aplicar_catalogo_ifs_rev13()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ifs_catalogo_versoes WHERE versao = 'REV13-2026-04') THEN
        START TRANSACTION;
        UPDATE ifs_itens SET ativo = 0 WHERE ativo = 1;
        UPDATE ifs_blocos SET ativo = 0 WHERE ativo = 1;

        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)', 1, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('REQUISITOS GERAIS', 2, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('BLOQUEIO DE FONTES DE ENERGIA', 3, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ANDAIMES', 4, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('CARGA SUSPENSA', 5, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('MÁQUINAS E FERRAMENTAS MANUAIS', 6, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE', 7, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS', 8, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS', 9, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ESCADAS, RAMPAS E PASSARELAS', 10, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ESCAVAÇÕES', 11, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ESPAÇO CONFINADO', 12, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('TRABALHO A QUENTE', 13, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('PRODUTOS QUÍMICOS - MEIO AMBIENTE', 14, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('TRABALHO EM ALTURA', 15, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ALPINISMO', 16, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('TELHADOS', 17, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM', 18, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)', 19, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('EXPOSIÇÃO A GASES / BENZENO', 20, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('CANTEIROS', 21, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('ATIVIDADE DE HIDROJATO', 22, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('NR 13 - CALDEIRA E VASOS DE PRESSÃO', 23, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('EMERGÊNCIAS', 24, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('COMPORTAMENTO', 25, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('MÃOS SEGURAS', 26, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('BOAS PRÁTICAS', 27, 1);
        INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('IFS', 28, 1);

        SET @bloco_id = NULL;
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.1', 'O serviço possui Procedimento, APR, APR na OS, PT, que contemplam os cenários de riscos, foram considerados todos os controles aplicáveis e estão implementados?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.2', 'Todos os campos dos formulários foram preenchidos e fechados, conforme padrão? Para acréscimo de executantes, estes foram inclusos em folha adicional liberada pelo responsável da tarefa?', 'C', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.3', 'O Procedimento, APR, APR na OS, PT está divulgada e possui assinatura de todos os executantes da tarefa e disponível na frente de serviço?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.4', 'O vigia do fogo conhece seus papeis e suas responsabilidade e esta atuando corretamente na frente de serviço de trabalho á quente?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.5', 'As tarefas da APR/PT, estão de acordo com o potencial de severidade em função do cenário?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.6', 'A APR, APR na OS e PT foi emitida e liberada por profissionais treinados e autorizados (carteirinha), e seguindo a alçada de liberação?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.7', 'A carteirinha de liberação emitida pelo Bancodoc, contempla todas as liberações necessárias para realização da função?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.8', 'DDS foi realizado, os colaboradores conhecem o tema abordado?', 'C', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 1 AND nome = 'CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '1.9', 'Outros:', '', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.1', 'O posto de trabalho possui água potável e copos disponíveis?', 'C', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.2', 'Os locais sem iluminação natural, foram mapeados e/ou estão em funcionamento um sistema de iluminação artificial adequado?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.3', 'A sinalização e o isolamento da área estão adequadas e compatíveis com a atividade, fixadas de forma que não ofereçam riscos e conforme OB-IO-010-058?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.4', 'Os EPI''s indicados são adequados aos riscos das atividades e dos locais de trabalho, estão em boa condição de uso e são substituídos sempre que necessário?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.5', 'Os colaboradores utilizam uniformes e estão em boas condições de uso?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.6', 'A área de trabalho está livre de obstáculos, materiais escorregadios e/ou saliências?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.7', 'As aberturas no piso estão protegidas e identificadas? As proteções são resistentes e estão fixadas corretamente?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.8', 'É cumprido o procedimento de apadrinhamento (identificação ou entrevistas)?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.9', 'O armazenamento de materiais possui acesso fácil e corredores?', 'C', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.10', 'Os resíduos gerados na área estão devidamente segregados e sem acúmulo? São descartados periodicamente em local apropriado?', 'C', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.11', 'Itens de abrangências mapeados estão implantados?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 2 AND nome = 'REQUISITOS GERAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '2.12', 'Outros*:', '', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.1', 'O Mapa de Bloqueio de fontes de energia foi preenchido corretamente seguindo os pontos de bloqueios que estão contemplados na APR, OS ou Procedimento Operacional?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.2', 'O solicitante do bloqueio foi treinado no procedimento OB-I0-010-069 de Bloqueio de fontes de energia e possui carteirinha de identificação?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.3', 'Todos os envolvidos no trabalho possuem seus cadeados individuais com etiqueta de identificação?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.4', 'A etiqueta do cadeado individual consta foto, nome, número de matricula, telefone de contato, nome da empresa?', 'C', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.5', 'O pré teste foi realizado/conferido, evidenciando que o sistema está livre de energia residual (mecânica, térmica, hidráulica, pneumática, elétrica, etc.) através da assinatura do responsável no documento de solicitação (APR e OS)?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.6', 'Nas caixas de bloqueios estão contidos no mínimo os pontos de bloqueios e/ou nº da Ordem de Serviço?', 'C', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 3 AND nome = 'BLOQUEIO DE FONTES DE ENERGIA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '3.7', 'Outros*:', '', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.1', 'Para atividades de montagens de andaimes: tipo torre ou tipo passarela com risco de queda acima de 10 metros, forro em vão aberto com com risco de queda acima de 6 metros, tipo guarda corpo temporário com risco de queda acima de 6 metros, tipo estrura de acesso com degraus e patamares com risco de queda acima de 6 metros, tipo torre com a base apoiada em piso estável e seguro com um único balanço com risco de queda acima de 6 metros, tipo balanço vertical com travamento em estrutura fixa, travando em: colunas; vigas e estruturas metálicas com risco de queda acima de 2 metros, tipo balanço com travamento em estrutura fixa travado em: colunas, vigas e estruturas metálicas com risco de queda acima de 2 metro, com risco de queda em corpo hidrico que possa causar afogamento, foi seguida alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.2', 'Os andaimes estão nivelados, alinhados e estaiados corretamente?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.3', 'Os andaimes possuem projeto e houve a necessidade da memoria de cálculo estrutural conforme procedimento?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.4', 'O projeto do aindaime está vinculado a ART do contrato ou do projeto específico?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.5', 'Andaimes de acesso e permanência de pessoas que estejam à 2 metros ou mais entre a base de trabalho e o piso, que passaram por revisão de projeto, foi revisada a APR e seguida a alçada de liberação conforme potencial classificado?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.6', 'A APR de montagem, desmontagem ou de alteração de andaime contempla o número do projeto e o título do tipo da estrutura a ser montada?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.7', 'As modificações foram avaliadas pelo projetista, alteradas no projeto e evidenciadas no campo de modificação no check-list de liberação de andaime?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.8', 'As plataformas de serviço nos andaimes tem largura mínima de 0,60 m e altura livre mínima de 1,75 m', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.9', 'Escadas de acesso atendem a largura mínima de 0,4 m (quarenta centímetros) e distância uniforme entre os degraus compreendida entre 0,25 m (vinte e cinco centímetros) e 0,3 m (trinta centímetros)?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.10', 'Guarda-corpos estão colocados a 0,50 m, 1,00 m e 1,50 m acima do estrado, fixado de modo a não se deslocar em qualquer direção?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.11', 'Os rodapés tem no mínimo 0,15 m de altura, nos níveis de trabalho?', 'B', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.12', 'Os pisos (mesmo metálicos) apresentam rugosidade para não permitir o escorregamento, possuem quebra vão e estão fixados?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.13', 'Os pisos de madeira, estão secos, possuem no minimo 0,38cm (trinta e oito milímetros) de espeçura, isento de nós, rachaduras ou outros defeitos, sendo proibido o uso de pintura, possuem quebra vão e estão fixados?', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.14', 'É atendida a proibição quanto a mesclagem de diferentes tipos de materiais na montagem (tipo Multidirecional ou tubular tipo roll)? Exeto para fixação dos andaimes e instalação de quebra vão.', 'A', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.15', 'O risco de abalroamento contra o andaime está controlado (ponte rolante, EMVI, tubulações, redes elétricas, pontos quentes, etc..)?', 'A', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.16', 'O check-list de liberação de montagem foi preenchido corretamente e estão no prazo? (30 dias, podendo ser revalidado a cada 30 dias, com prazo mázimo de 6 meses).', 'B', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.17', 'O andaime possui iluminação em seus acessos e locais de trabalho?', 'B', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.18', 'Andaimes montados com distância inferior a 3,0 m de rede elétrica ou outros equipamentos energizados, foi autorizado por profisional habilitado e com procedimentos específicos seguindo a NR10?', 'A', 18, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.19', 'Foi realizado o pré uso do andaime pela equipe usuária conforme formulário do OB-IO-633-002?', 'C', 19, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.20', 'Torres de andaimes não estaiadas ou não fixadas à estrutura, está com em altura até 4 (quatro) vezes a menor a dimensão da base de apoio?', 'B', 20, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.21', 'Está sendo cumprida a proibição de montar, desmontar, descer, subir com condições climáticas adversas (chuvas, ventos fortes, nevoeiros)?', 'A', 21, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.22', 'Inexistência de acúmulo de materiais, ferramentas e peças soltas no piso do andaime?', 'A', 22, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.23', 'Os  andaimes  possuem  placas  indicativas  durante  a  montagem  e  utilização:  ANDAIME  LIBERADO  (placa verde) ou ANDAIME NÃO LIBERADO (placa vermelha) ?', 'B', 23, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.24', 'Andaimes com a placa “ANDAIME NÃO LIBERADO” estão com isolamentos para impedir trânsito de pessoas embaixo da estrutura?', 'B', 24, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.25', 'A área em volta da montagem/desmontagem, está isolada seguindo as recomendações do OB-IO-010-058?', 'C', 25, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.26', 'Andaimes móveis possuem trava nos rodízios? Existe regra específica para movimentação com a plataforma isenta de materiais e colaboradores?', 'A', 26, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.27', 'As peças disponíveis nos gaveteiros, ou que compõe o andaime estão livres de anomalias? (amassados, quebras, trincas, soldas de ligação, soldas para reparos/emendas, furos, oxidação e desgastes)', 'A', 27, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.28', 'Os gaveteiros possuem projeto, check de liberação e check list de pré uso?', 'B', 28, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.29', 'Os gaveteiros estão posicionados em locais seguros, de forma a não oferecer risco de batida contra e de queda das peças armazenadas?', 'B', 29, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.30', 'Os materiais armazenados no gaveteiro estãor armazenados por tipos e agrupados de acordo com o comprimento e características específicas?', 'B', 30, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 4 AND nome = 'ANDAIMES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '4.31', 'Outros*:', '', 31, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.1', 'Para atividades com içamento de pessoas com uso de gaiola, içamentos utilizando dois guindastes simultâneos ou um guindaste e uma ponte; içamento de carga com distância inferior a 6m a linhas de alta tensão energizadas e/ou linhas de gás viva foi seguida a alçada de liberação da APR como catálogo de risco,(Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.2', 'O operador tem conhecimento sobre o peso da carga e está compatível com a tabela de carga do equipamento?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.3', 'As patolas do equipamento estão 100% abertas durante a operação?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.4', 'O Guindates / guindauto está devidamente nivelado?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.5', 'Está sendo respeitada a distância de segurança em relação aos cabos de linhas de transmissão energizadas?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.6', 'Em caso de patolamentos sobre lajes ou galerias foi emitido laudo por profissional habilitado  garantindo a resistência do local?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.7', 'Existem medidas de controles efetivas para que os colaboradores NÃO fiquem sob a carga suspensa em área de movimentção de carga ou durante a atividade de içamento? E estão sendo cumpridas?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.8', 'A tabela de carga do equipamento está disponível de forma visível?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.9', 'Existe plano de Rigging emitido e aprovado por profissional qualificado para içamentos considerados CRÍTICOS? (Quando o peso da carga somado aos acessórios ultrapassar ou for igual a 10ton, colisão com pontes rolantes, trabalhos que necessitem de 2 (dois) ou mais equipamentos de guindar, Sobre equipamentos pressurizados, energizados ou sobre sistemas que, se danificados podem causar a parada de uma unidade produtiva, Qualquer içamento realizado por guindaste que for trabalhar acima de 80% da capacidade registrada na tabela de carga deste equipamento e Trabalho sobre lajes e/ou galerias).', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.10', 'O içamento está sendo realizado em condições climáticas favoráveis?', 'B', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.11', 'A carga, está sendo guiada por dispositivo de segurança adequado (cordas, etc...)? Os sinaleiros ou supervisores de içamento estão a uma distancia segura da carga?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.12', 'Os acessórios de içamento (cabos de aço, ganchos com travas , cintas, etc.) estão em boas condições e foram verificados pelo  sinaleiro / operador na inspeção de pré uso?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.13', 'Está sendo usado o "quebra-quinas" sobre as quinas "vivas"?', 'B', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.14', 'O Sinaleiro está identificado com colete refletivo ?', 'B', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.15', 'Existe um sistema eficaz de comunicação entre Sinaleiro e Operador ?', 'A', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.16', 'Para içamentos de carga abaixo de 10ton. com guindastes e/ou caminhão munck está sendo preenchido o Anexo II conforme OB-IO-010-010?', 'A', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 5 AND nome = 'CARGA SUSPENSA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '5.17', 'Outros*:', '', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.1', 'Foi realizada a inspeção de pré uso nas máquinas e ferramentas? O formulário utilizado determina itens a serem avaliados, parâmentos de aceitabilidade,  itens que interditam claramente os equipamentos , tag ou número, metodologia (C/NC), frequência, Código de ação para itens Não Conformes (ex.:1 - Corrigir, 2 - Impeditivo), Plano de Ação e está preenchido com o nome do responsável pela inspeção?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.2', 'As partes móveis estão protegidas adequadamente com proteções de fábrica, com abertura que não permita inserção de membros superiores e inferiores dos colaboradores? (NR12)', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.3', 'As máquinas possuem dispositivo de parada de emergência junto ao Operador?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.4', 'As máquinas possuem dispositivos contra acionamento desautorizados?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.5', 'As máquinas estão aterrados eletricamente?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.6', 'Os elementos estruturais estão em perfeito estado e sem deformações?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.7', 'As máquinas possuem conjuntos mecânicos limpos, livre de vazamentos, bem fixados, em bom estado de conservação e mangueiras com indicação de pressão máxima  e proteção  adequada contra projeção?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.8', 'As máquinas possuem fiações e ligações elétricas bem fixadas e devidamente isoladas? As ferramentas manuais elétricas possuem duplo isolamento.', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.9', 'As máquinas e ferramentas elétricas possuem tomadas e conexões padronizadas, sem defeitos, sinalizadas com tensão identificada?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.10', 'Os condutores de alimentação das ferramentas elétricas portáteis são manuseados de forma que não sofram torção, ruptura e abrasão?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.11', 'As esmerilhadeiras utilizadas possuem dispositivo  "Dead Man" conforme padrão de utilização de esmerilhadeiras ?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.12', 'É atendida a proibição quanto a utilização de equipamentos portáteis rotativos para afiar ferramentas?', 'B', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.13', 'As mangueiras das ferramentas pneumáticas, possuem engate com corrente de segurança?', 'B', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.14', 'As ferramentas manuais, estão em boas condições de uso (sem cabeças de cogumelo, cabos fixados)?', 'B', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.15', 'Existe prática da não improvisação de ferramentas?', 'B', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.16', 'As ferramentas e materiais utilizados no processo produtivo estão organizadas, dispostas e  armazenadas em locais específicos para essa finalidade?', 'B', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.17', 'As ferramentas manuais que possuam gume ou ponta são protegidas quando não estiverem sendo utilizadas?', 'B', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.18', 'Durante pausas temporárias ou prolongadas, as ferramentas são desconectadas da fonte de energia com o objetivo de eliminar riscos provenientes de funcionamento acidental?', 'B', 18, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.19', 'As marretas que são utilizadas são da linha PRO (Profissional, especifica para a Siderurgia)?', 'B', 19, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.20', 'Foi feita um estudo de outras ferramentas para substituição da marreta na atividade?', 'C', 20, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 6 AND nome = 'MÁQUINAS E FERRAMENTAS MANUAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '6.21', 'Outros*:', '', 21, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.1', 'Os quadros de energia estão fechados em bom estado de conservação, livre de objetos, limpos, desobstruídos e com sinalização quanto ao perigo de choque elétrico e identificação de colaboradores autorizados a operar?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.2', 'O risco de contato acidental com componentes energizados está controlado?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.3', 'Todos os painéis e tomadas elétricas estão identificados corretamente e limpos?', 'B', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.4', 'Todos os painéis elétricos possuem disjuntores diferenciais de segurança?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.5', 'Os cabos e extensões elétricas são mantidos suspensos e em boas condições?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.6', 'Trabalhos nas proximidades de rede de alta tensão respeitam a distância de segurança de acordo com a tensão nominal da instalação elétrica, conforme determina a NR 10?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.7', 'É respeitada a proibição de realização de serviços individualmente, em instalações elétricas energizadas em Alta Tensão ou no Sistema Elétrico de Potência - SEP?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 7 AND nome = 'SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '7.8', 'Outros*: As extensões eletrica possuem tag de identificação para auxiliar na identificação', '', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.1', 'O EMVI passou pela inspeção periódica de equipamentos móveis e possui QR Code do Frota Legal válida? Todos os equipamentos da contratada estão como status liberado no Frota Legal?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.2', 'O EMVI possui as inspeções de pré-uso preenchidas corretamente? O formulário utilizado determina itens a serem avaliados, parâmentos de aceitabilidade,  itens que interditam claramente os equipamentos , tag ou número, metodologia (C/NC), frequência, Código de ação para itens Não Conformes (ex.:1 - Corrigir, 2 - Impeditivo), Plano de Ação e está preenchido com o nome do responsável pela inspeção?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.3', 'Todos os itens impeditivos estão em conformidade?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.4', 'Os operadores possuem CNH válida, categoria compatível com o equipamento e autorização para operação do EMVI?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.5', 'O EMVI possui sua altura (interna e externa), capacidade de carga máxima identificados no equipamento e faixa refletivas em bom estado?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.6', 'O EMVI possui cinto de segurança e os demais dispositivos de segurança funcionando?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.7', 'Todos os equipamentos móveis possuem alarme sonoro de ré, iluminação de advertência demais partes elétricas em funcionamento?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.8', 'Caminhões básculas possuem dispositivo inibidor de acionamento indevido de báscula e dispositivo indicador de posição de báscula erguida?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.9', 'O EMVI possui escadas, plataformas e corrimãos em bom estado de conservação, limpos, desobstruídos, com piso anti - derrapante e dimensões adequadas?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.10', 'O EMVI está isento de vazamentos de óleo e/ou combustíveis?', 'B', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.11', 'O Veículo/ Equipamento possui sistema de aterramento caso  transporte inflamáveis ou explosivos?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.12', 'É mantido o distanciamento mínimo de 7,5 m e sinalização de segurança para abastecimento?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.13', 'Os pneus e rodas estão em condições adequadas de uso?', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.14', 'Os EMVI possui dispositivo de retenção mecânica (calços) e está sendo utilizado em atividades de carga e descarga e/ou quando estacionados?', 'A', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.15', 'O Manual do equipamento está disponível dentro da cabine?', 'C', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.16', 'Os EMVI possuem cabine fechada e climatizada (Interclima - ar quente/ar frio ou Ar condicionado)?', 'B', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.17', 'Os Caminhões e Guindastes, possuem todos os DIPS e estes estão alinhados e com ausência de quebra e/ou derretimento?', 'A', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.18', 'Os operadores utilizam uniformes com listras reflexivas?', 'B', 18, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 8 AND nome = 'EMVI - EQUIPAMENTOS MÓVEIS / VEÍCULOS INDUSTRIAIS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '8.19', 'Outros:', '', 19, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.1', 'Um Rotograma está disponível no veículo e contém minimamente: interferências existentes no trajeto, trechos de maior risco, pontos de maior segurança recomendados para paradas em caso de emergência/pane, mapa do trajeto, velocidades máximas permitidas, possíveis rotas alternativas?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.2', 'Está implementado Plano de Gerenciamento de Fadiga e é possível evidenciar as ações de controle definidas neste plano?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.3', 'Os adesivos (altura, proibido falar com motorista, faixas refletivas, proibido permanecer na cabine com veículo em movimento ) estão íntegros.', 'B', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.4', 'Os dispositivos elétricos e luminosos do veículo estão em pleno funcionamento?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.5', 'Os pneus e rodas estão em condições adequadas de uso?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.6', 'Ausência de trincas no parabrisas do lado do motorista? (trincas maiores que 30cm)', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.7', 'O Cronotacógrafo está aferido e em pleno funcionamento?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.8', 'O extintor está com lacre, carga completa e devidamente pressurizado (manômetro no verde)? O A data de validade da carga em dia? Existe algum dano físico no extintor (amassado, corte na mangueira, etc.)? Ficha de inspeção com registro mensal?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.9', 'Escadas de acesso possuem antiderrapante e corrimão?', 'B', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.10', 'Checklist determina itens críticos para operação segura do equipamento incluindo dispositivos de sinalização de segurança para casos de emergência? O formulário utilizado determina itens a serem avaliados, parâmentos de aceitabilidade,  itens que interditam claramente os equipamentos , tag ou número, metodologia (C/NC), frequência, Código de ação para itens Não Conformes (ex.:1 - Corrigir, 2 - Impeditivo), Plano de Ação e está preenchido com o nome do responsável pela inspeção?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.11', 'Os dispositivos utilizados nas saídas de emergência (martelinho, alavanca, etc) estão adequados conforme definido pelo fabricante?', 'B', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.12', 'Os calços estão adequados conforme padrão e disponíveis?', 'B', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.13', 'Bancos e cintos de segurança dos ocupantes estão em boas condições?  Banco motorista ônibus rodoviário deve possuir amortecimento, ajuste de altura e encosto de cabeça.', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.14', 'Os Ônibus possuem todos os DIPS e estes estão alinhados, e com ausência de quebra e/ou derretimento?', 'A', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 9 AND nome = 'VEÍCULOS FRETADOS  - TRANSPORTE DE PESSOAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '9.15', 'Outros*:', '', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.1', 'A escada móvel está posicionada em local isento de risco de contato acidental com equipamentos e redes elétricas?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.2', 'A escada móvel é presas/amarradas na estrutura em que será apoiada ou o serviço é realizado em dupla para garantir a estabilidade ?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.3', 'A escada móvel possui sapatas antiderrapantes ?', 'C', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.4', 'As escadas móveis Tipo Tesoura possui comprimento máximo de 6 m ? Escada móveis extensoras possui comprimento máximo de 7 metros ?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.5', 'As escadas móveis Tipo Tesoura possui limitador de espaço ?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.6', 'As escadas móveis são construídas ou revestida em material não-condutor ou possuir indicação de “uso proibido para atividades com eletricidade".', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.7', 'As escadas, rampas e/ou passarela estão em boas condições de uso? Há aberturas no piso das passarelas e rampas? Os desníveis de piso, possuem degraus, conforme NR 18?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.8', 'As escadas tipo plataforma, rampas e/ou passarelas possuem guarda-corpo de 1,20m com travessas a 0,70m e rodapé de 0,20m?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.9', 'As rampas são providas de peças transversais para apoio dos pés?', 'B', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 10 AND nome = 'ESCADAS, RAMPAS E PASSARELAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '10.10', 'Outros*:', '', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.1', 'Existe um Plano de Escavação com acompanhamento por profissional legalmente habilitado, quando aplicável? (Engenheiro Civel ou Geólogo com CREA)', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.2', 'Antes da execução das atividades de apicoamento, demolição, escavação e furação/corte, foi realizada uma análise das possíveis interferências, tais como: tubulações de gás, dutos enterrados de energia e telefonia, abastecimento de água potável e industrial, esgoto sanitário e industrial, drenagem pluvial, sistema de combate a incêndio e aterramento com utilização  de equipamento de detecção georadar (GPR) e/ou Pipe Locator.', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.3', 'O tráfego de veículos próximos à área de escavação foi desviado?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.4', 'Nas bordas da escavação, está sendo resguardada uma faixa sem sobrecarga de, no mínimo, uma vez a medida da profundidade ou 1m se profundade for inferior?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.5', 'O risco de desmoronamento está controlado (rampas de 45° ou escoramento)?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.6', 'O acesso a escavação é seguro?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.7', 'A escavação está com proteção nas laterais e são resistentes contra queda de pessoas ou veículos?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.8', 'Os resíduos gerados na escavação estão sendo destinados corretamente?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.9', 'A escavação permite a saída e o resgate rápido de colaboradores?', 'B', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 11 AND nome = 'ESCAVAÇÕES' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '11.10', 'Outros*:', '', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.1', 'Para atividades em atmosferas IPVS foi seguida a alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.2', 'A Permissão de Trabalho em Espaço Confinado (PETEC)  foi emitida, liberada, divulgada e assinada, e se encontra na entrada do espaço confinado sendo cumprida integralmente?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.3', 'Existe um "vigia" qualificado em contato com as pessoas dentro do espaço confinado? As pessoas que entraram no espaço confinado deixaram os crachás com o vigia?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.4', 'Todos os envolvidos na atividade de espaço confinado, possuem autorização com treinamento vigente, possuem identificação de habilitação para trabalho em espaço confinado?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.5', 'A iluminação é adequada para execução dos serviços no interior dos espaços confinados, observando as áreas classificadas e de risco de explosão ?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.6', 'A forma/método de comunicação entre o interior e exterior dos espaços confinados estão adequados? Caso seja utilizado rádios de comunicação, os mesmos são intrinsecamente seguros?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.7', 'A tensão da rede de iluminação é limitada a 24 Volts e Cabos elétricos/extensões não possui emendas para áreas molhadas?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.8', 'Todos equipamentos elétricos são intrinsecamente seguros e possui a identificação (EX)?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.9', 'O cenário de espaço confinado está em conformidade com o plano de resgate informado na PETEC?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.10', 'Os equipamentos de medição foram testados (bump test)?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.11', 'Foi verificada a necessidade de implantar sistema de ventilação/exaustão?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 12 AND nome = 'ESPAÇO CONFINADO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '12.12', 'Outros*:', '', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.1', 'Para atividades de trabalho a quente em áreas classificadas (zona 0 e 1), em espaços confinados com risco de atmosfera explosiva, tanques e tubulações de gases combustíveis, inflamáveis e criogênicos, foi seguida a alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.2', 'O equipamento oxiacetilênico/máquina de solda recebeu inspeção de pré-uso?  O formulário utilizado determina itens a serem avaliados, parâmentos de aceitabilidade,  itens que interditam claramente os equipamentos , tag ou número, metodologia (C/NC), frequência, Código de ação para itens Não Conformes (ex.:1 - Corrigir, 2 - Impeditivo), Plano de Ação e está preenchido com o nome do responsável pela inspeção?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.3', 'As mangueiras do conjunto oxiacetilênico possuem válvula contra retrocesso de chama junto a caneta e ao cilindro? Estão sendo utilizadas somente as Válvulas Reguladoras de pressão: Oxigênio / Acetileno / GLP, dos fabricantes autorizados pela Gerdau, devido à aprendizado de acidente?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.4', 'Somente é permitido emendar mangueiras conjunto oxiacetilênico por meio do uso de conector, em conformidade com as especificações técnicas do fornecedor/fabricante ?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.5', 'Os leitos de cabos elétricos e vias de acesso e circulação de pessoas estão protegidos contra fagulhas, respingos de solda e projeção de partículas de ferramentas rotativas?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.6', 'Existe extintor de incêndio na frente de serviço e os mesmos estão adequados ao uso, limpos e desimpedidos? Esses passaram por inspeção mensal?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.7', 'Os cilindros de gás são mantidos em posição vertical, fixados e distantes de chamas, fontes de centelhamento, calor ou de produtos inflamáveis,com carrinhos em boas condições seguindo projeto do greendocs?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.8', 'São transportados na posição vertical, com capacete rosqueado, por meio de equipamentos apropriados, devidamente fixados, evitando-se colisões.', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.9', 'Os equipamentos oxi-acetileno (mangueiras, conexões) estão perfeito estado de conservação?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.10', 'Máquinas de solda elétrica possuem os jacarés e cabos de aterramento em boas condições?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.11', 'Esta sendo utilizado barreira física (Biombos) onde a risco de projeção de partículas, acessos indevidos ou isolamento de riscos operacionais?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 13 AND nome = 'TRABALHO A QUENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '13.12', 'Outros*:', '', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.1', 'As FISPQ/FDS estão disponíveis na frente de serviço/local de armazenamento e estocagem atualizadas conforme PGG-010-020, as pessoas envolvidas têm conhecimento registrado através de lista de divulgação e as recomendações estão sendo seguidas?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.2', 'É obedecida a proibição de utilização de querosene, thinner e água raz? (Para as tarefas que requerem o uso destes produtos químicos deverá ser utilizado um substituto mais seguro.)', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.3', 'Existe líquido inflamável com ponto de fulgor ≤ 37,8°C? Os produtos inflamáveis e perigosos são acondicionados e transportados corretamente? Possuem autorização da Gerdau para sua utilização e esta encontra-se na frente de serviço?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.4', 'Os produtos químicos estão rotulados de forma legível, por etiqueta com o nome do produto, composição química, sua concentração, data de envase e de validade, e nome do responsável pela manipulação ou fracionamento?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.5', 'Em caso de manuseio de produto químico fracionado foi verificada a compatibilidade da embalagem nova com o produto químico e descontaminação da embalagem; e estado de conservação da embalagem?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.6', 'Os resíduos perigosos e contaminados estão acondicionados conforme OB-PGG-010-003?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.7', 'Os locais de armazenamento de produtos químicos possuem proteção contra derramamentos acidentais, estão devidamente trancados e há identificação clara das pessoas autorizadas a manuseá-los?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.8', 'A ausência de vazamento de produto químico direto no solo?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.9', 'Há KIT de Emergência Ambiental devidamente identificado e com os dispositivos de contenção?', 'B', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 14 AND nome = 'PRODUTOS QUÍMICOS - MEIO AMBIENTE' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '14.10', 'Outros*:', '', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.1', 'Para os serviços em altura, acima de 2m, foi verificado a aplicabilidade de um plano de resgate para o cenário da tarefa?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.2', 'As linhas de vida possuem indicação da capacidade máxima de carga e plano de manutenção preventiva.', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.3', 'Os pontos de ancoragem para cintos de segurança foram definidos e estão sendo usados 100% do tempo?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.4', 'As condições climáticas estão favoráveis (ausência de ventos fortes, chuvas, descargas atmosféricas  e umidade) para execução da atividade?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.5', 'O isolamento abaixo dos trabalhos em altura é suficiente, estão sinalizados corretamente, e estão sendo respeitados, conforme padrão Gerdau?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.6', 'As ferramentas manuais utilizadas em altura estão amarradas?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.7', 'Foi realizado pelo usuário o pré uso dos dispositivos de segurança (linha de vida, trava queda, cinto de segurança, entre outros)?O formulário possui itens que interditam claramente os equipamentos e está preenchido com o nome do responsável pela inspeção, TAG do equipamento e não possuir campos em branco e/ou rasuras?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.8', 'É seguida a proibição de trabalho em altura de forma solitária?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.9', 'Em atividades sobre andaimes, o cinto de segurança está ancorado em tubos já montados e travados nas duas extremidades?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 15 AND nome = 'TRABALHO EM ALTURA' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '15.10', 'Outros*:', '', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.1', 'Para atividades que envolvam alpinismo foi emitido PT e foi seguida a alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.2', 'As atividades que envolvam alpinismo, são executadas por no mínimo 2 profissionais em acesso de cordas que envolvam certificados pelos órgãos iratas, Abendi ou Aneac ?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.3', 'Todos os alpinistas possuem carteirinhas de identificação constando no mínimo: Nome completo do indivíduo certificado, data de certificação, data de validade da certificação, nível da certificação, nome do organismo de certificação, número único de identificação, assinatura do individuo certificado e foto ?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.4', 'Foram analisados a ocorrência de descargas atmosféricas (raios), ventos fortes, chuva intensa, iluminação inadequada, poeira, ruído excessivo, gases, proximidade e contato com a rede elétrica energizada e fontes de calor ou contato com produtos abrasivos?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.5', 'O dimensionamento dos dispositivos de deslocamento e ancoragem provisórios e permanentes estão instaladas e usadas de acordo com os procedimentos de segurança e conforme projeto elaborado por profissional habilitado?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 16 AND nome = 'ALPINISMO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '16.6', 'Outros*:', '', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.1', 'Para atividades em telhados foi emitido PT e seguida a alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU)?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.2', 'Foi analisada a possibilidade de utilização de plataforma elevatória por pessoa devidamente habilitada, em substituição a andaimes, balancins, passarelas de telhado ou outros equipamentos afins?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.3', 'A frente de trabalho tem supervisão de IRATA III?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.4', 'As atividades de acesso por corda são executadas por colaborador certificado? Existe a obrigatoriedade de ser executada por pelo menos 2 colaboradores, sendo um deles Supervisor?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.5', 'O telhado está livre do acúmulo de materiais?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.6', 'O dimensionamento dos dispositivos de deslocamento, ancoragem provisórios e permanentes foi realizado por profissional legalmente habilitado?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.7', 'Todo trabalho em telhado é provido de cabos-vida ou pontos para instalação de cabos-vida provisórios, com uso obrigatório do cinto de segurança tipo paraquedista com duplo talabarte?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.8', 'O sistema de fixação possui laudo emitido por profissional habilitado ?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.9', 'É respeitada a proibição do acesso ao telhado em condições de umidade, ventos fortes e eminência de chuva ou de apenas uma pessoa?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.10', 'As proteções contra quedas, seja para acesso ou execução das tarefas, estão instaladas e usadas  de acordo c/ os procedimentos de segurança e conforme projeto elaborado por profissional habilitado? Foi emitido a ART das respectivas proteções?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.11', 'Foi verificado nas atividades o risco de sobreposição e/ou interferência com a área operacional?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.12', 'Existem pranchões (duralumínio antiderrapante) instalados adequadamente para os colaboradores pisarem, se necessário? Os pranchões sobre o telhado estão devidamente travados, que permitam a movimentação com segurança?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.13', 'A rede de proteção contra quedas está instalada abaixo de 2 metros da área de trabalho para atividades em altura com vãos livres superiores à 10 metros?', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.14', 'É claro para os executantes e seguida a proibição de pisar diretamente sobre as telhas?', 'A', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.15', 'Foram analisados os riscos de interferências com pontes rolantes e adotadas medidas de controle aplicáveis?', 'B', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.16', 'Existe um sistema efetivo de comunicação entre as pessoas que estão trabalhando no telhado e uma pessoa em solo, (vigia)?', 'B', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.17', 'O trava-quedas atende aos seguintes requisitos: Mosquetão giratório 360º para que não haja torção do cabo, mola de proteção antitravamento, possui dupla trava de segurança e travamento simultâneo em dois pontos da linha de vida.', 'B', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.18', 'O içamento de ferramentas será executado através de cordas e em recipientes adequados;', 'B', 18, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 17 AND nome = 'TELHADOS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '17.19', 'Outros*:', '', 19, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.1', 'Há Sinalização de trânsito adequada? Há sinaleiros para todos os equipamentos móveis e/ou frentes de serviços?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.2', 'Existem "Leiras" com altura mínima da metade da roda do maior veículo?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.3', 'Existe a disponibilidade de caminhões pipas suficientes, para umidificação e limpeza das vias?', 'C', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.4', 'Todos os sinaleiros fazem uso do colete refletivo e apitos?', 'C', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.5', 'Existe sistema de comunicação, eficaz para controle de tráfego ?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.6', 'Há acesso seguro para pedestres, sinalizado e isolado?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.7', 'Em locais com trânsito de equipamentos móveis e ferrovia, o vão livre está com altura de 5,5m e com sinalização adequada?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 18 AND nome = 'SERVIÇOS EM VIAS DE TRÂNSITO E TERRAPLANAGEM' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '18.8', 'Outros*:', '', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.1', 'Há banheiros químicos para cada 20 colaboradores em atividade? Estão instalados em locais adequados e com cobertura?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.2', 'Estão mantidos em estado de asseio e higiene diário e possui materiais de higiene?', 'C', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.3', 'Estão instalados em compartimentos individuais separados masculino e feminino?', 'C', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.4', 'Estão dotados de portas providas de fecho?', 'C', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.5', 'O local é de fácil acesso e não permitindo um deslocamento superior a 150m (posto de trabalho)?', 'C', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.6', 'Sanitários químicos estão isolados, com  distância segura de áreas classificadas, tubulações de gás, selos pote, linha férrea, produtos químicos/combustíveis e área de manobra de veículos/equipamentos?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 19 AND nome = 'BANHEIROS QUÍMICOS (OBRA/CONTRATOS CURTOS)' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '19.7', 'Outros*:', '', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.1', 'Para as seguintes atividades: em linha de gás, onde não é possível instalação de raquetes / Atividades de corte/solda de tubulação em linha viva / Trepanação (Perfuração) em rede de gás / Atividades que necessitam de utilização de equipamento de respiração autônoma / Atividades com uso de equipamentos com uso de linha de ar respirável, foi seguida alçada de liberação da APR como catálogo de risco (Gerente e SESMT GERDAU) ?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.2', 'Está sendo respeitada a proibição de utilização de qualquer linha de ar comprimido que não seja dedicada, para atividades que necessitam de ar respirável ?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.3', 'Para atividades de pintura em tubulações de gases que estejam pressurizadas, está sendo respeitada a proibição de utilização de jateamento? Caso seja imprescindível o jateamento da tubulação de gás, a mesma está sendo retirada de operação, bloqueada e purgada para execução da atividade ?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.4', 'Os equipamentos do sistema de ar respirável foram inspecionados pela Gestão de Terceiros Gerdau e possuem o selo de liberação?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.5', 'Os equipamentos do sistema de ar respirável possuem plano de manutenção preventiva?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.6', 'Foi realizado inspeção de pré-uso para os sistemas de ar respirável (Arcofil) / equipamentos de respirador autônomo?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.7', 'Sistema de ar respirável( Arcofil) possui filtros para partículas, óleo, vapores orgânicos, odores , umidade (água), regulagem de pressão, válvula de alívio, indicador de saturação dos filtros, captação de ar de um local isento de contaminação, sistema de engate rápido especifico para aplicação?', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.8', 'É monitorado o teor de contaminantes, principalmente o CO em Arcofil em linha de compressor de óleo ?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.9', 'Os cilindros possuem teste hidrostático conforme especificação do fabricante e por período equivalente a 5 anos?', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.10', 'O detector portátil ( Bigás ou Multigás)  está sendo utilizado na área onde é exigido?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.11', 'O detector possui sistema audiovisual e vibratório . O display / visor do detector de gás foi verificado se ao ligar o aparelho há existência de algum segmento de indicação de valor queimado, dificultando a leitura efetuada?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.12', 'O detector está calibrado, carregado e possui etiqueta informando a data de calibração do aparelho e da próxima calibração conforme OB-IO-010-011?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.13', 'O detector esta sendo utilizado no local correto? Altura do peito.', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.14', 'Colaboradores com exposição rotineira tem o risco de exposição ao Benzeno mapeado no Bancodoc (conferir carteirinha). Exposição rotineira pode ser 1 vez por mês, 1 vez por semana ou qualquer outra periodicidade. Deve haver rotina na exposição.', 'A', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.15', 'Colaboradores participaram da campanha do PPEBOB - Programa de prevenção a exposição ocupacional ao Benzeno (Aplicável para quem esteve exposto por períodos > 6 meses).', 'A', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.16', 'A máscara semifacial está limpa em seu interior, seus cartuchos estão em boas condições e dentro da validade (validade do cartucho para exposição esporádica 6 meses. Exposição diária validade 2 meses. Deve estar registrado no cartucho data de validade).', 'A', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 20 AND nome = 'EXPOSIÇÃO A GASES / BENZENO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '20.17', 'Outros:', '', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.1', 'O canteiro da contratada possui alvará?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.2', 'Layout do canteiro está disponível no local?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.3', 'Diagrama unifilar do sistema elétrico está disponível no canteiro?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.4', 'O canteiro se encontra limpo e organizado?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.5', 'O canteiro possui placa visível com identificação da empresa e dos seus responsáveis?', 'C', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.6', 'O Mapa de Risco do canteiro foi elaborado?', 'C', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.7', 'Canteiro possui o piso de todas as áreas das instalações provisórias com concreto, brita, lastro ferroviário ou calcário rebritado?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.8', 'Área de trânsito de pessoas e veículos/equipamentos está segregada?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.9', 'Iluminação e sinalização está instalada? (Placas de velocidade máxima, caminho seguro, etc.)', 'B', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.10', 'Quando em atividade noturna, iluminação de emergência está instalada?', 'A', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.11', 'Containers e demais estruturas metálias estão aterrados?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.12', 'Houve necessidade de alteração do layout original? O Alvará foi revisado?', 'A', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.13', 'Cabeamentos elétricos estão embutidos em eletrodutos?', 'B', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.14', 'Disjuntores, Interruptores e tomadas estão identificados com tensão existente?', 'C', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.15', 'Há instalação de cobertura que garanta o conforto térmico? (exceto para containers com ar condicionado)', 'B', 15, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.16', 'Instalações elétricas provisórias estão dimensionadas por profissional habilitado, com ART?', 'A', 16, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.17', 'Tendas possuem projeto de montagem, com base de fixação e pontos de ancoragem (mínimo quatro pontos), aterramento das estruturas metálicas, garantia de que não acumule água sobre a lona, “chapéu chinês”.', 'B', 17, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.18', 'Há plano de inspeção e manutenção periódica para tendas que forem permanecer por mais de 30 dias?', 'C', 18, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.19', 'Piso interno das Tendas encontram-se sem ressaltos?', 'C', 19, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.20', 'Os vestiários e banheiros atendem os dimensionamentos da NR-24?', 'B', 20, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 21 AND nome = 'CANTEIROS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '21.21', 'Outros:', '', 21, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.1', 'Para atividades com uso de equipamentos com alta pressão (Hidrojato) que não atendam a todos os requisitos do check list do procedimento para atividades com hidrojato, foi seguida alçada de liberação da APR como catálogo de risco ( Gerente e SESMT GERDAU) ?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.2', 'A Distância de segurança é superior a 7,5 m do jatista ? Ou existe uma barreira física implementada que garanta que outra pessoa não seja atingida pelo jato de alta pressão ?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.3', 'A distância do sentido de projeção de material é superior a 45 m do jatista ?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.4', 'É possível o contato visual entre operadores e 1º jatista e 2º jatista?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.5', 'Existe o limitador na tubulação para uso de rabicho ?', 'A', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.6', 'Os colaboradores possuem treinamento para hidrojato identificado na carteirinha com validade anual?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.7', 'O pré-uso dos acessórios de hidrojateamento foi preenchido corretamente, e os itens impeditivos (1 a 19) apresentou não conformidade ?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.8', 'Foi preenchido check list de hidrojateamento com pressão acima de 70 Bar com liberação do solicitante da Gerdau, se todos os itens marcados for SIM, a atividade será de risco APR A, se houver um item com NÃO a atividade será catálogo de risco (CR) ?', 'A', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.9', 'Nas operações há pelo menos três pessoas envolvidas (02 jatistas e 01 motorista) ? (Na ausência de 01 ou mais dos colaboradores a atividade dever ser imediatamente paralisada.)', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.10', 'Foi realizado o pré uso para  máquina de alta pressão (lavadoras) e este foi preenchido corretamente?', 'B', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 22 AND nome = 'ATIVIDADE DE HIDROJATO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '22.11', 'Outros*:', '', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 23 AND nome = 'NR 13 - CALDEIRA E VASOS DE PRESSÃO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '23.1', 'O recipiente pressurizado possui placa de identificação com código de projeto, ano de fabricação, fabricante, pressão máxima de trabalho admissível (PMTA), pressão de teste hidrostático e categoria do vaso?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 23 AND nome = 'NR 13 - CALDEIRA E VASOS DE PRESSÃO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '23.2', 'O recipiente pressurizado dispõe de acesso fácil e seguro para as atividades de operação e manutenção, incluindo guarda corpo ou dispositivo de ancoragem adequado contra queda de pessoas?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 23 AND nome = 'NR 13 - CALDEIRA E VASOS DE PRESSÃO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '23.3', 'O recipiente pressurizado estão insentos de  danos (pintura, corrosão, trincas, deformações, etc.) nas superfícies pressurizadas ou alguma condição que constitua risco grave e iminente ou deterioração atestada?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 23 AND nome = 'NR 13 - CALDEIRA E VASOS DE PRESSÃO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '23.4', 'As válvulas de segurança do recipiente pressurizado estão instaladas em boas condições, com lacre preservado, identificadas e calibradas conforme certificado de calibração correspondente?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 23 AND nome = 'NR 13 - CALDEIRA E VASOS DE PRESSÃO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '23.5', 'Outros*:', '', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 24 AND nome = 'EMERGÊNCIAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '24.1', 'O extintor está lacrado, com carga completa e pressurizado (manômetro na zona verde)? A data de validade está atualizada? Há algum dano físico no extintor, como amassados ou cortes na mangueira? Existe a ficha de inspeção com registros mensais?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 24 AND nome = 'EMERGÊNCIAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '24.2', 'Os colaboradores conhecem o ponto de encontro para emergências mais próximo ao local da atividade?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 24 AND nome = 'EMERGÊNCIAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '24.3', 'Outros*:', '', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.1', 'Colaborador tem olhos na atividade, sem pressa, com equilíbrio, tração e firmeza, manteve posição ao ser observado e adequada a execução da atividade?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.2', 'Colaborador Utiliza os EPI`s previstos para atividade de forma correta?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.3', 'O colaborador está posicionado de forma correta sem os riscos de: colisões ou impactos, prensamento, quedas (sejam no mesmo nível ou em níveis diferentes), queimaduras, choques elétricos, e exposição a contaminantes (por inalação, absorção ou ingestão)?', 'A', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.4', 'Colaborador utiliza ferramenta de forma correta sem improviso?  E estas estão em condições seguras para uso?', 'A', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.5', 'Os colaboradores atendem a proibição quanto ao porte de ferramentas que possuem gume ou ponta em bolsos?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.6', 'Colaborador cumpre os Procedimentos, OS, APR e PT?', 'A', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.7', 'O colaborador demonstra aplicação dos 5S?', 'B', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.8', 'Está sendo cumprida a proibição de utilizar adornos como: brincos, pulseiras, relógios, cordões, anéis, etc?', 'B', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.9', 'Todos os colaboradores das frentes de serviços, próximas às áreas operacionais, conhecem os riscos específicos a que estão expostos. (Entrevista)', 'A', 9, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.10', 'É seguido a proibição de não fumar em locais de riscos ou que não estejam designados para uso de cigarro?', 'B', 10, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.11', 'É atendida a regra de não utilizar o celular em área operacional ou portar durante a condução e operação de Equipamentos Móveis, Ponte Rolante e em Áreas Classificadas?', 'A', 11, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.12', 'A atendida a proibição de uso de barba ao usar máscara?', 'B', 12, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.13', 'Foi aberta Recusa Tarefa para condições físicas ou sistêmicas na àrea de atuação/atendimento passivas de serm identificadas e paralizada a execução?', 'A', 13, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 25 AND nome = 'COMPORTAMENTO' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '25.14', 'Outros*:', '', 14, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.1', 'O executante conhece o programa mãos seguras e sabe o objetivo do mesmo?', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.2', 'O executante consegue citar ao menos um dos dispositivos aprovados no programa mãos seguras referente à sua área ou atividade?', 'B', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.3', 'Os dispositivos aprovados estão disponíveis e de fácil acesso?', 'B', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.4', 'Caso aplicável, o uso dos dispositivos estão descritos como controles nos documentos de liberação da atividade?', 'B', 4, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.5', 'Os dispoisitivos são utilizados de forma correta?', 'B', 5, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.6', 'Os dispositivos estão em boa condição de uso e disponíveis em quantidade suficiente?', 'B', 6, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.7', 'Os dispositivos utilizados nas tarefas, são bem dimencionados de forma não permitir sua exposição ao risco.', 'A', 7, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 26 AND nome = 'MÃOS SEGURAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '26.8', 'Outros:', '', 8, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 27 AND nome = 'BOAS PRÁTICAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '27.1', 'As boas práticas criadas pela parceira, estão disponíveis em todas as frentes de serviço que se aplicam, e essas foram e descritas nos controles sistêmicos das atividades?', 'A', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 27 AND nome = 'BOAS PRÁTICAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '27.2', 'Os colaboradores da parceira, reconhecem as boas práticas implementadas e estão treinados na implantação das mesmas como controles de segurança, nas atvidades que se aplicam?', 'C', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 27 AND nome = 'BOAS PRÁTICAS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '27.3', 'Outros:', '', 3, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 28 AND nome = 'IFS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '28.1', 'Foi elaborado e enviado para a Gestão de Terceiros, o plano de ação das últimas três IFS realizadas? Está sendo cumprido o prazo de 07 dias úteis para envio do plano de ação.', 'B', 1, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 28 AND nome = 'IFS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '28.2', 'Foram enviadas para a Gestão de Terceiros as evidências de correção das não conformidades conforme os prazos definidos (Potencial A: Imediato, B e C: 7 dias úteis)?', 'A', 2, 1);
        SELECT id INTO @bloco_id FROM ifs_blocos WHERE ativo = 1 AND ordem = 28 AND nome = 'IFS' ORDER BY id DESC LIMIT 1;
        INSERT INTO ifs_itens (bloco_id, codigo, descricao, potencial, ordem, ativo)
        VALUES (@bloco_id, '28.3', 'Os desvios encontrados nas IFS estão sendo tratados de forma sistêmica impedindo a reincidência?', 'C', 3, 1);

        INSERT INTO ifs_catalogo_versoes (versao, descricao)
        VALUES ('REV13-2026-04', 'Formulario de Inspecao Frente de Servicos - Revisao 13 - abril/2026');
        COMMIT;
    END IF;
END$$
DELIMITER ;
CALL aplicar_catalogo_ifs_rev13();
DROP PROCEDURE IF EXISTS aplicar_catalogo_ifs_rev13;

SELECT COUNT(*) AS blocos_ativos FROM ifs_blocos WHERE ativo = 1;
SELECT COUNT(*) AS itens_ativos FROM ifs_itens WHERE ativo = 1;
SELECT COUNT(*) AS itens_com_potencial FROM ifs_itens WHERE ativo = 1 AND potencial IN ('A','B','C');

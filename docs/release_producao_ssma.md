# Publicação SSMA em produção

Esta entrega é baseada em `origin/main` e não substitui a produção pela branch de homologação.

## Escopo

- Relato de Desvios e Buffer de Desvios.
- Observação Comportamental.
- Gestão SSMA, Agendamento SSMA e Relatório de Aderência.
- Gestor SSMA e política global de acesso aos registros de SSMA.
- Confirmações globais em modal.

Análise Crítica HS, Recrutamento e Seleção e Ressarcimentos PCP-M não fazem parte desta versão.

## Proteção obrigatória dos dados

1. Colocar a aplicação em janela de manutenção ou impedir gravações durante o backup e a migração.
2. Gerar backup completo da base de produção com rotinas, gatilhos e eventos, quando existirem.
3. Conferir se o arquivo de backup tem tamanho plausível e testar a restauração em uma base temporária.
4. Executar `release_producao_ssma_precheck.sql` e salvar o resultado.
5. Executar, nesta ordem:
   1. `criar_modulo_observacao_comportamental.sql`
   2. `adicionar_exclusao_logica_observacao_comportamental.sql`
   3. `criar_modulo_desvios.sql`
   4. `evoluir_matriz_risco_desvios.sql`
   5. `criar_gestor_ssma.sql`
6. Executar `release_producao_ssma_poscheck.sql` e comparar as contagens das tabelas preexistentes com o precheck.
7. Somente depois publicar a aplicação.

Os scripts são aditivos e reexecutáveis. Eles não contêm `DROP`, `TRUNCATE`, exclusão de registros nem alteração de valores de negócio preexistentes. A sincronização de permissões apenas concede os acessos equivalentes à nova regra.

## Configuração do Render

- Preservar todas as variáveis atuais da produção.
- Manter `UPLOAD_ROOT=/var/data/uploads` e o disco persistente atual.
- Configurar `GROQ_API_KEY` e, se usado, `GROQ_MODEL`.
- Não substituir o disco nem alterar o mount path durante o deploy.

## Reversão

Se houver falha funcional, reimplantar o commit anterior da aplicação. Não remover as tabelas ou colunas novas: mantê-las preserva qualquer registro criado depois da migração e permite corrigir a aplicação sem perda de dados.

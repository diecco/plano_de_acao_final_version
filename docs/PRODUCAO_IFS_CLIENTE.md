# Implantação da IFS do Cliente em produção

Este pacote contém somente a IFS do Cliente e os ajustes indispensáveis da
IFS interna para operar com o catálogo Rev. 13 compartilhado.

## Antes do deploy

1. Suspender o serviço para impedir lançamentos durante a troca do catálogo.
2. Confirmar o schema de produção com `SELECT DATABASE();`.
3. Executar, nesta ordem e por inteiro:
   1. `docs/atualizar_catalogo_ifs_rev13.sql`
   2. `docs/criar_ifs_cliente.sql`
4. Confirmar que os resultados finais informam 28 blocos ativos e que as
   tabelas `ifs_cliente_%` foram criadas.

Os scripts preservam inspeções antigas: a revisão anterior do catálogo é
inativada, não excluída. A nova IFS do Cliente nasce sem registros de teste.

## Deploy

Publicar a branch `release/ifs-cliente-producao` em `main` somente após a
confirmação dos SQLs. Depois, forçar o deploy no Render caso o serviço tenha
permanecido suspenso durante o push.

## Validação após o deploy

1. Reativar o serviço e confirmar o health check.
2. Entrar com gestor de SSMA e confirmar o item **IFS do Cliente** dentro de
   **Gestão SSMA**.
3. Confirmar que um usuário sem perfil de gestor não vê nem acessa o módulo.
4. Criar uma IFS sem desvios e validar nota, listagem, detalhe e relatório PDF.
5. Criar uma IFS com resposta **Não**, gerar uma ação e conferir o vínculo no
   plano de ação com origem **IFS do Cliente**.
6. Avaliar um item `Outros*` para confirmar a compatibilidade sem potencial.
7. Anexar o PDF original, visualizar, baixar e substituir pela edição.
8. Confirmar filtros, ordenação, indicadores, edição e exclusão lógica.
9. Confirmar que uma IFS interna antiga continua exibindo os itens da revisão
   usada no lançamento.

## Consultas de conferência

```sql
SELECT versao, descricao, aplicado_em
FROM ifs_catalogo_versoes
WHERE versao = 'REV13-2026-04';

SELECT COUNT(*) AS blocos_ativos
FROM ifs_blocos
WHERE ativo = 1;

SELECT COUNT(*) AS itens_ativos
FROM ifs_itens
WHERE ativo = 1;

SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME LIKE 'ifs_cliente_%'
ORDER BY TABLE_NAME;
```

## Rollback operacional

Em caso de erro de aplicação, reverter somente o commit de entrega e fazer
novo deploy. Não excluir as tabelas nem os registros criados. O catálogo
anterior permanece preservado e os dados da IFS do Cliente devem permanecer
para auditoria e correção posterior.

# Matriz de permissionamento

Esta matriz registra o comportamento esperado antes da refatoração estrutural
de `routes.py`.

| Recurso | Permissão exigida | Exceção administrativa |
| --- | --- | --- |
| Plano de ação | `acesso_plano_acao` | Sim |
| SSMA (HS, Recusa, APR, AP e IFS) | `acesso_ssma` | Sim |
| Meu calendário SSMA | `pode_ser_lider_ssma` | Não; administrador também precisa ser líder |
| Executar agendamento SSMA | `pode_ser_lider_ssma` e ser o líder do registro | Não |
| Gerenciar agendamentos SSMA | `pode_criar_agendamento_ssma` | Sim |
| Relatório de aderência SSMA | `pode_criar_agendamento_ssma` | Sim |
| Melhorias | `acesso_melhoria` | Sim |
| Gestão de pessoas | `acesso_gestao_pessoas` | Sim |
| Treinamentos e exportações | `acesso_treinamentos` | Sim |
| Procedimentos | `acesso_procedimentos` | Sim |
| PCP-M | `acesso_pcpm` | Sim |

Regras gerais:

- `login_required` autentica; não substitui autorização de módulo ou registro.
- Perfis ausentes ou fora de `basico`, `intermediario`, `avancado` e
  `administrador` invalidam a sessão.
- O perfil `intermediario` precisa obrigatoriamente possuir centro de custo.
- Permissão de módulo e permissão por registro são cumulativas.
- Links da interface não são controles de segurança; toda rota deve validar acesso.
- As permissões armazenadas na sessão continuam sendo a fonte atual durante esta
  etapa, para evitar uma mudança simultânea no modelo de sessão.

Escopo de usuários nos relatórios e exportações de treinamentos:

- `administrador` e `avancado`: todos os usuários ativos.
- `intermediario`: usuários ativos do mesmo centro de custo.
- `basico` e demais perfis: somente o próprio usuário.
- Ausência do centro de custo ou do identificador necessário resulta em nenhum
  usuário permitido; uma lista vazia nunca é interpretada como acesso global.

Operações integrais de treinamento:

- Edição e exclusão de um treinamento completo exigem perfil `avancado` ou
  `administrador`.
- Participar de um treinamento não concede permissão para alterar ou excluir o
  registro que também pode conter outros participantes.

Decisões mantidas nesta etapa:

- PCP-M continua global para qualquer usuário com `acesso_pcpm`.
- Procedimentos e matrizes continuam globais para usuários com
  `acesso_procedimentos`.

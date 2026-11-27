# TrackPlan BI API v1

API somente leitura para alimentar modelos semânticos do Power BI. A primeira
versão cobre Relatos de Ocorrências, Observações Comportamentais, Auditoria de
Padrão e as IFS Tradimaq e do Cliente.

## Configuração no Render

Cadastre duas variáveis de ambiente no serviço de homologação:

- `POWER_BI_API_USER`: usuário técnico. Sugestão: `powerbi_trackplan`.
- `POWER_BI_API_KEY`: segredo aleatório longo e exclusivo do ambiente.

Exemplo para gerar um segredo localmente:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Não salve o segredo no repositório, no código ou em uma planilha.

## Autenticação

O Power BI deve utilizar autenticação **Basic** sobre HTTPS. O usuário e a
senha correspondem às duas variáveis acima. Para testes técnicos, a API também
aceita a chave em `X-API-Key` ou como `Bearer`, mas esses formatos não são a
configuração recomendada para o modelo publicado.

## Recursos

- `GET /api/bi/v1`
- `GET /api/bi/v1/ocorrencias`
- `GET /api/bi/v1/observacoes-comportamentais`
- `GET /api/bi/v1/observacoes-comportamentais-itens`
- `GET /api/bi/v1/auditorias-padrao`
- `GET /api/bi/v1/ifs`

O recurso `ifs` possui o campo `origem_ifs`, com os valores `IFS Tradimaq` e
`IFS do Cliente`.

O recurso `observacoes-comportamentais-itens` retorna uma linha para cada
comportamento crítico identificado. Relacione `registro_id` ao campo `id` de
`observacoes-comportamentais`. Os campos `categoria_nome`, `item_descricao`,
`descricao_estratificacao` e `quantidade` permitem montar a distribuição e o
ranking dos principais desvios no Power BI.

## Parâmetros comuns

| Parâmetro | Formato | Finalidade |
| --- | --- | --- |
| `data_inicio` | `AAAA-MM-DD` | Primeiro dia incluído |
| `data_fim` | `AAAA-MM-DD` | Último dia incluído |
| `centro_custos` | códigos separados por vírgula | Restringe um ou mais centros |
| `atualizado_apos` | ISO 8601 | Retorna inclusões e alterações posteriores |
| `pagina` | inteiro a partir de 1 | Página solicitada |
| `tamanho_pagina` | 1 a 2000 | Quantidade de registros por página |

Resposta:

```json
{
  "versao": "v1",
  "pagina": 1,
  "tamanho_pagina": 500,
  "total_registros": 1250,
  "total_paginas": 3,
  "dados": []
}
```

## Power Query

Comece pela URL raiz do recurso e configure as credenciais Basic na fonte de
dados. O exemplo abaixo percorre todas as páginas:

```powerquery
let
    BaseUrl = "https://trackplan-teste.onrender.com/api/bi/v1/ocorrencias",
    TamanhoPagina = 1000,
    LerPagina = (Pagina as number) as record =>
        Json.Document(
            Web.Contents(
                BaseUrl,
                [
                    Query = [
                        pagina = Text.From(Pagina),
                        tamanho_pagina = Text.From(TamanhoPagina)
                    ]
                ]
            )
        ),
    Primeira = LerPagina(1),
    QuantidadePaginas = Primeira[total_paginas],
    Paginas = if QuantidadePaginas = 0 then {} else {1..QuantidadePaginas},
    Registros = List.Combine(List.Transform(Paginas, each LerPagina(_)[dados])),
    Tabela = Table.FromRecords(Registros)
in
    Tabela
```

No Power BI Desktop, escolha **Basic** quando o programa solicitar a
credencial da fonte. Depois da publicação, configure a mesma credencial na
conexão do modelo semântico e programe a atualização.

## Premissas da versão inicial

- A API não permite inclusão, alteração ou exclusão.
- O acesso técnico enxerga os dados corporativos disponibilizados pelos quatro
  recursos. A restrição por centro de custos ocorre por filtro da consulta e
  pelo modelo do Power BI.
- A seção editorial da análise crítica permanece em planilha externa.
- Prontos, Fadiga e IPL ficam fora da primeira versão.
- Nenhum endpoint expõe anexos, senhas, hashes de arquivos ou dados de sessão.

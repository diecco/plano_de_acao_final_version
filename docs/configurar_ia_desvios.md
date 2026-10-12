# Configuração da análise de desvios com Groq

1. Crie uma chave no console do Groq.
2. No serviço de homologação do Render, abra **Environment** e adicione:

   - `GROQ_API_KEY`: chave secreta do Groq;
   - `GROQ_MODEL`: `openai/gpt-oss-20b` (opcional; este já é o padrão).

3. Execute `docs/evoluir_matriz_risco_desvios.sql` na base de homologação.
4. Faça o deploy da aplicação e teste o botão **Analisar com IA**.

A chave nunca deve ser incluída no código, no repositório ou enviada ao navegador.
O cadastro manual continua disponível quando o serviço de IA estiver indisponível.

Nesta primeira versão, somente os dados textuais do desvio são enviados. Relator,
matrícula, usuário conectado, centro de custos e anexos não são enviados à IA.

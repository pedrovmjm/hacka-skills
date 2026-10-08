# Checklist de segurança

Percorra cada item. Para cada "sim, há problema", colete evidência (arquivo:linha + reprodução)
antes de registrar.

## A. Identidade e autenticação
- [ ] De onde vem a identidade do chamador? Corpo/query/header controlado pelo cliente (`user_id`, `role`, `X-User`) não é identidade.
- [ ] Rotas sensíveis exigem autenticação? Há rotas "esquecidas" sem dependência de auth?
- [ ] Troca de perfil/papel é feita no servidor ou só na UI?
- [ ] Tokens/segredos: hard-coded, em logs, em respostas, em repositório?

## B. Autorização e posse de recurso (IDOR)
- [ ] Toda leitura/escrita por ID (`/items/{id}`, `conversation_id`, `thread_id`) verifica se o recurso pertence ao chamador ou ao tenant dele?
- [ ] Listagens filtram por dono/tenant no **servidor**?
- [ ] Ações privilegiadas (aprovar, excluir, editar de terceiros, ver visão de time) verificam papel e vínculo?
- [ ] UUID não substitui controle de acesso, porque costuma vazar em respostas, URLs e logs.

## C. Injeção
- [ ] SQL montado com f-string/concatenação/`%`? Procure `execute(f"`, `.format(` próximo a SQL.
- [ ] Comandos de sistema com entrada externa (`subprocess`, `os.system`, `shell=True`, `child_process`).
- [ ] `eval`/`exec`/`pickle`/`yaml.load` sem `SafeLoader`/`new Function` com dados externos.
- [ ] Templates renderizados a partir de string do usuário.

## D. Arquivos e recursos locais
- [ ] Caminhos derivados de entrada externa: há `resolve()` + verificação de prefixo dentro de uma raiz allowlist? Symlinks?
- [ ] Ferramentas que leem/escrevem arquivos, URLs (SSRF) ou executam código.
- [ ] Upload: tipo, tamanho e destino controlados?

## E. Saída e XSS
- [ ] React: `dangerouslySetInnerHTML`, `innerHTML`, `href={userInput}` (`javascript:`), `eval`.
- [ ] Backend devolvendo HTML com dado não escapado.
- [ ] Conteúdo do usuário (notas, nomes, mensagens) renderizado em outro contexto (visão de time, admin).

## F. Exposição de informação
- [ ] Exceções devolvidas ao cliente (`str(e)`, `traceback`, `detail=repr(...)`).
- [ ] Respostas com campos internos (hash, flags, dados de outros usuários, paths do servidor).
- [ ] Logs com PII/segredos.

## G. Configuração web e infraestrutura
- [ ] CORS: `allow_origins=["*"]` com `allow_credentials=True`; origens refletidas.
- [ ] Debug/reload ativo em imagem de produção; servidor de dev do Vite em produção.
- [ ] Headers (CSP, X-Content-Type-Options, frame-ancestors) ausentes, normalmente LOW.
- [ ] Docker: roda como root, copia `.env`/banco para a imagem, portas desnecessárias.
- [ ] Dependências sem pin ou com CVE conhecido (verificar versão no manifesto).

## H. Agentes LLM e ferramentas (OWASP LLM Top 10)
- [ ] **Excessive Agency (LLM06):** ferramentas com poder maior que o necessário (ler qualquer arquivo, rodar shell, HTTP arbitrário).
- [ ] Ferramentas sensíveis executam **sem HITL** ou com HITL contornável.
- [ ] HITL: a aprovação verifica **quem aprova**, se pertence ao fluxo, se a ação pendente é a mesma que será executada (TOCTOU), e se é idempotente (aprovar duas vezes)?
- [ ] Prompt injection: texto do usuário/ferramenta pode escolher ferramenta e argumentos sem validação?
- [ ] Estado do grafo/checkpoint: isolado por usuário/thread? Configuração global mutável compartilhada entre requisições?
- [ ] Histórico/memória acessível por quem não é dono.

## I. Integridade e auditabilidade
- [ ] Ações importantes registram quem, quando e o quê? O registro pode ser forjado pelo cliente (`reviewer` vindo do corpo)?
- [ ] Operações compostas são atômicas (transação)? Há janela de leitura-modifica-escrita?
- [ ] Dados podem ser alterados retroativamente sem trilha (ex.: editar presença de mês fechado)?
